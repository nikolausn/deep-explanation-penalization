import torch
import torchvision
import torchvision.datasets as datasets
import sys
import numpy as np
import torch.utils.data as utils
import torch
from torch.utils.data import DataLoader
from torch.utils.data import Subset
from torchvision import  transforms
import pickle as pkl
from os.path import join as oj
import matplotlib.pyplot as plt
import torch.optim as optim
from torch.optim import lr_scheduler
import os
import torch
import torchvision
import argparse
import sys
import matplotlib.pyplot as plt
import numpy as np
import torch.utils.data as utils
from torch import nn
from numpy.random import randint
import torchvision.models as models
import time
import os
import copy
from tqdm import tqdm
sys.path.append('..')
import cd
import utils
import json

with open('config.json') as json_file:
    data = json.load(json_file)
model_path = os.path.join(data["model_folder"], "feature_models")
dataset_path =os.path.join(data["data_folder"],"calculated_features")

 

# Training settings
parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
parser.add_argument('--batch_size', type=int, default=32, metavar='N',
                    help='input batch size for training (default: 64)')

parser.add_argument('--epochs', type=int, default=5, metavar='N',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--lr', type=float, default=0.01, metavar='LR',
                    help='learning rate (default: 0.01)')
parser.add_argument('--momentum', type=float, default=0.9, metavar='M',
                    help='SGD momentum (default: 0.5)')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--regularizer_rate', type=float, default=0.0, metavar='N',
                    help='how heavy to regularize lower order interaction (AKA color)')
args = parser.parse_args()

regularizer_rate = args.regularizer_rate

num_epochs = args.epochs

device = torch.device(0)

# load model
model = models.vgg16(pretrained=True)
model.classifier[-1] = nn.Linear(4096, 2)
model = model.classifier.to(device)

datasets = utils.load_precalculated_dataset(dataset_path)

dataset_sizes= {x:len(datasets[x]) for x in datasets.keys()}
dataloaders = {x: torch.utils.data.DataLoader(datasets[x], batch_size=args.batch_size,
                                             shuffle=True, num_workers=4)
              for x in datasets.keys()}



       
#we use the same weights as for the original datasets. This could go both ways.
num_one = 0
for data, target,_ in dataloaders['train']:
    num_one +=target.sum().cpu().item()
  
cancer_ratio = num_one/len(datasets['train'])
not_cancer_ratio =num_one/len(datasets['train'])
not_cancer_ratio = 1- cancer_ratio
cancer_weight = 1/cancer_ratio
not_cancer_weight = 1/ not_cancer_ratio

weights = np.asarray([not_cancer_weight, cancer_weight])
weights /= weights.sum()
weights = torch.tensor(weights).to(device)
print(weights)


def train_model(model,dataloaders, criterion, optimizer, num_epochs=25):
    since = time.time()
    val_acc_history = []
    val_loss_history = []
    train_loss_history = []
    
    train_acc_history = []
    train_cd_history= []
    

    best_model_wts = copy.deepcopy(model.state_dict())
    best_loss = 10.0
    
    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train_no_patches', 'val']:
            if phase == 'train_no_patches':
                optimizer.step()
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_loss_cd = 0.0
            running_corrects = 0

            # Iterate over data.
            for i, (inputs, labels, cd_features) in tqdm(enumerate(dataloaders[phase])):
                inputs = inputs.to(device)
                labels = labels.to(device)
                cd_features = cd_features.to(device)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == 'train_no_patches'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    # backward + optimize only if in training phase
                    if phase == 'train_no_patches':
                        (loss).backward()
                        optimizer.step()

                # statistics
                running_loss += loss.item() * inputs.size(0)
                running_loss_cd +=0 * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_cd_loss = running_loss_cd / dataset_sizes[phase]
       
            epoch_acc = running_corrects.double() / dataset_sizes[phase]
  

            print('{} Loss: {:.4f} Acc: {:.4f} CD Loss : {:.4f}'.format(
                phase, epoch_loss, epoch_acc, epoch_cd_loss))

            # deep copy the model
            if phase == 'val':
                val_acc_history.append(epoch_acc.item())
                val_loss_history.append(epoch_loss)
            if phase == 'train_no_patches':
                train_loss_history.append(epoch_loss)
                train_cd_history.append(epoch_cd_loss)
                train_acc_history.append(epoch_acc.item())
                
            if phase == 'val' and epoch_loss < best_loss:
            
                best_loss = epoch_loss
                best_model_wts = copy.deepcopy(model.state_dict())

 

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))
    print('Best val loss: {:4f}'.format(best_loss))

    # load best model weights

  
    hist_dict = {}
    hist_dict['val_acc_history'] = val_acc_history
    hist_dict['val_loss_history'] = val_loss_history
    
    hist_dict['train_acc_history'] = train_acc_history

    hist_dict['train_loss_history'] = val_loss_history
    hist_dict['train_cd_history'] = train_cd_history
    model.load_state_dict(best_model_wts)
    return model,hist_dict #TODO hist
    

params_to_update = model.parameters()
criterion = nn.CrossEntropyLoss(weight = weights.double().float())
optimizer_ft = optim.SGD(params_to_update, lr=args.lr, momentum=args.momentum)

#optimizer_ft = optim.Adam(params_to_update, weight_decay = 0.001)
model, hist_dict = train_model(model, dataloaders, criterion, optimizer_ft, num_epochs=num_epochs)
pid = ''.join(["%s" % randint(0, 9) for num in range(0, 20)])
torch.save(model.state_dict(),oj(model_path, pid + ".pt"))
import pickle as pkl
hist_dict['pid'] = pid
hist_dict['regularizer_rate'] = -1
hist_dict['seed'] = args.seed
hist_dict['batch_size'] = args.batch_size
hist_dict['momentum'] = args.momentum

hist_dict['learning_rate'] = args.lr



pkl.dump(hist_dict, open(os.path.join(model_path, pid +  '.pkl'), 'wb'))