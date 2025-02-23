import torch
import torch.nn as nn


# Base class for time series neural network models
# 时序模型的基类
class TimeSeriesNN(nn.Module):
    '''
    Input shape: (batch_size, input_len, input_channels)
    Output shape: (batch_size, output_len, output_channels)
    The overall architecture is direct multistep (DMS), rather than iterated multi-step (IMS). That is, directly predicting T future time steps (T>1).
    Usually input_channels == output_channels, but for generalizability, we set them separately.
    '''
    def __init__(self, input_len, output_len, input_channels, output_channels):
        super(TimeSeriesNN, self).__init__()
        self.input_len = input_len
        self.input_channels = input_channels
        self.output_len = output_len
        self.output_channels = output_channels

    # placeholder for forward function, to be implemented by subclasses
    def forward(self, x): # x: (batch_size, input_len, input_channels)
        pass
    
    # evaluate the model on a given dataset
    def evaluate(self, data,
                loss=nn.functional.mse_loss,
                mode='data_loader',
                device='cpu', # note that the default device is 'cpu'
                verbose=1
                ):
        """
        Return: loss on the given dataset
        """
        if mode == 'data_loader': # If mode is 'data_loader', data should be a DataLoader object
            '''
            data: DataLoader object
            '''
            data_loader = data
            self.eval()  # switch to evaluation mode
            total_loss = 0.0

            if verbose==1:
                try:
                    import tqdm
                except ImportError:
                    raise ImportError("Please install tqdm to use progress bars.\nCommand: conda install tqdm")
                with torch.no_grad():
                    for inputs, targets in tqdm.tqdm(data_loader): # inputs: (batch_size, input_len, input_channels), targets: (batch_size, output_len, output_channels)
                        inputs, targets = inputs.to(device), targets.to(device) # Transfer data to GPU (if available)
                        if hasattr(self, 'label_len') and self.label_len > 0:
                            # If the model has `label_len` attribute, decoder input is needed, and label should be taken into consideration
                            # 如果模型含有label_len属性，说明前向传播过程需要解码器输入，训练过程考虑label
                            dec_inp = torch.cat([
                                    targets[:, :self.label_len, :],
                                    torch.zeros_like(targets[:, -self.pred_len:, :]).float().to(device)
                                    ],
                                    dim=1
                                    ).float().to(device) # Use targets as decoder input in the first `label_len` time steps, and zeros for the rest
                            outputs = self(inputs, dec_inp)
                            outputs = outputs[:, -self.pred_len:, :].to(device) # Only take the last `pred_len` time steps # 取待预测时间范围内的数据
                            targets = targets[:, -self.pred_len:, :].to(device) # Only take the last `pred_len` time steps # 取待预测时间范围内的数据
                        else:
                            # If the model doesn't have `label_len` attribute, the decoder input is not needed
                            # 如果模型不含有label_len属性，说明前向传播过程不需要解码器输入
                            outputs = self(inputs)
                        total_loss += loss(outputs, targets).item() * inputs.size(0)
                return total_loss / len(data_loader.dataset)
            elif verbose==0:
                with torch.no_grad():
                    for inputs, targets in data_loader: # inputs: (batch_size, input_len, input_channels), targets: (batch_size, output_len, output_channels)
                        inputs, targets = inputs.to(device), targets.to(device) # Transfer data to GPU (if available)
                        outputs = self(inputs)
                        total_loss += loss(outputs, targets).item() * inputs.size(0)
                return total_loss / len(data_loader.dataset)
        
        elif mode == 'numpy': # If mode is 'numpy', data should be a tuple of numpy arrays
            '''
            data: (inputs, targets)
            - inputs: (batch_size, input_len, input_channels)
            - targets: (batch_size, output_len, output_channels)
            '''
            inputs, targets = data
            assert inputs.ndim==3, 'inputs should be a 3D numpy array'
            assert targets.ndim==3, 'targets should be a 3D numpy array'
            assert inputs.shape[0]==targets.shape[0], 'inputs and targets should have the same batch size'
            assert inputs.shape[1:]==(self.input_len, self.input_channels), 'inputs should have shape (batch_size, input_len, input_channels)'
            assert targets.shape[1:]==(self.output_len, self.output_channels), 'targets should have shape (batch_size, output_len, output_channels)'
            inputs, targets = torch.from_numpy(inputs).float(), torch.from_numpy(targets).float()
            self.eval()  # switch to evaluation mode
            with torch.no_grad():
                outputs = self(inputs)
                result = loss(outputs, targets).item()
                return result