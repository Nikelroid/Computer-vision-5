# -*- coding: utf-8 -*-
"""classification_AlexNet (1).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1_raeFAe9ORWV4Dkj2Vq5T3icMBdOr6qM
"""

!pip install -U albumentations
!pip install opencv-python-headless==4.1.2.30

import matplotlib.pyplot as plt
from pandas.core.common import flatten
import cv2
import copy
import numpy as np
import random

import torch
from torch import nn
from torch import optim
import torch.nn.functional as F
from torchvision import datasets, transforms, models
from torch.utils.data import Dataset, DataLoader

import albumentations as A
from albumentations.pytorch import ToTensorV2


import glob
from tqdm import tqdm

import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt
import os
import time

from google.colab import drive 
drive.mount('/content/drive')
import os
os.chdir('/content/drive/My Drive/Vision')

train_data_path = 'Data/Train/'
test_data_path = 'Data/Test/'

train_image_paths = [] 
classes = [] 


for data_path in glob.glob(train_data_path + '/*'):
    classes.append(data_path.split('/')[-1]) 
    train_image_paths.append(glob.glob(data_path + '/*'))
    
train_image_paths = list(flatten(train_image_paths))
random.shuffle(train_image_paths)

print('train_image_path example: ', train_image_paths[0])
print('class example: ', classes[0])



#3.
# create the test_image_paths
test_image_paths = []
for data_path in glob.glob(test_data_path + '/*'):
    test_image_paths.append(glob.glob(data_path + '/*'))

test_image_paths = list(flatten(test_image_paths))

print("Train size: {}\nTest size: {}".format(len(train_image_paths), len(test_image_paths)))

idx_to_class = {i:j for i, j in enumerate(classes)}
class_to_idx = {value:key for key,value in idx_to_class.items()}

from torch.utils.data import Dataset

class LandmarkDataset(Dataset):
    def __init__(self, image_paths, transform=False):
        self.image_paths = image_paths
        self.transform = transform
        
    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image_filepath = self.image_paths[idx]
        image = cv2.imread(image_filepath)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        label = image_filepath.split('/')[-2]
        label = class_to_idx[label]
        if self.transform is not None:
            image = self.transform(image=image)["image"]
        
        return image, label

train_transforms = A.Compose(
    [
        A.Resize(height=227, width=227),
        A.RandomBrightnessContrast(p=0.5),
        A.MultiplicativeNoise(multiplier=[0.5,2], per_channel=False, p=0.2),
        A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        A.RandomBrightnessContrast(brightness_limit=(-0.1,0.1), contrast_limit=(-0.1, 0.1), p=0.5),
        ToTensorV2(),
    ]
)

test_transforms = A.Compose(
    [
        A.Resize(height=227, width=227),
        A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ToTensorV2(),
    ]
)

trainset = LandmarkDataset(train_image_paths,train_transforms)
valset = LandmarkDataset(test_image_paths,test_transforms)

print('The shape of tensor for 50th image in train dataset: ',trainset[49][0].shape)
print('The label for 50th image in train dataset: ',valset[49][1])

from torch.utils.data import DataLoader

trainloader = DataLoader(
    trainset, batch_size=256, shuffle=True,num_workers=2
)


valloader = DataLoader(
    valset, batch_size=1024, shuffle=False,num_workers=2
)

testloader = valloader

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
device

import torchvision
from torchvision import transforms

import matplotlib.pyplot as plt

fig = plt.figure(figsize=(20, 4))

for i in range(20):
    fig.add_subplot(2, 10, i + 1)
    image, label = trainset[i]
    plt.imshow(image.permute(1, 2, 0).numpy())
    plt.title(classes[label])
    plt.axis('off')

plt.show()

def train_epoch(net: nn.Module, criterion: nn.Module, optimizer: torch.optim.Optimizer, dataloader: torch.utils.data.DataLoader,   accs_train ,loss_train):

    epoch_loss = 0
    epoch_true = 0
    epoch_all = 0
    i = 0

    # Set model to training mode
    net.train()

    # zero the parameter gradients
    optimizer.zero_grad()

    with tqdm(enumerate(dataloader), total=len(dataloader)) as pbar:
        for i, (x, y) in pbar: 

            # Transfer data to device
            x = x.to(device)  
            y = y.to(device)

            # forward
            p = net(x)

            # loss eval
            loss = criterion(p, y)
            epoch_loss += float(loss)

            # predict 
            predictions = p.argmax(-1)
            epoch_all += len(predictions)
            epoch_true += (predictions == y).sum()
            
            # Computes accuracy and loss
            pbar.set_description(f'Loss: {epoch_loss / (i + 1):.3e} - Acc: {epoch_true * 100. / epoch_all:.2f}%')


            # Backward the error
            loss.backward()
            optimizer.step()

            # zero the parameter gradients
            optimizer.zero_grad()
          
        accs_train.append(float(epoch_true / epoch_all))
        loss_train.append(float(epoch_loss / (i + 1)))
    return accs_train,loss_train

def eval_epoch(net: nn.Module, criterion: nn.Module, dataloader: torch.utils.data.DataLoader,    accs_test ,loss_test ):

    epoch_loss = 0
    epoch_true = 0
    epoch_true_topfive = 0
    epoch_all = 0
    i = 0

    # Set model to evaluate mode
    net.eval()

    with torch.no_grad(), tqdm(enumerate(dataloader), total=len(dataloader)) as pbar:
        for i, (x, y) in pbar:

            # Transfer data to device
            x = x.to(device)
            y = y.to(device)

            # forward
            p = net(x)

            # loss eval
            loss = criterion(p, y)
            epoch_loss += float(loss)

            # predict 
            predictions = p.argmax(-1)
            epoch_all += len(predictions)
            epoch_true += (predictions == y).sum()

            pbar.set_description(f'Loss: {epoch_loss / (i + 1):.3e} - Acc: {epoch_true * 100. / epoch_all:.2f}% ')

        accs_test.append(float(epoch_true / epoch_all))
        loss_test.append(float(epoch_loss / (i + 1)))
    return accs_test,loss_test

class AlexNet1(nn.Module):
    def __init__(self, num_classes: int = 15, dropout: float = 0.5) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=4, stride=4),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(12544, 4096),
            nn.ReLU(inplace=True),
            nn.Linear(4096, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

net = AlexNet1().to(device)
net

criterion = nn.CrossEntropyLoss().to(device)
optimizer = torch.optim.Adam(net.parameters(), lr=1e-4)


epochs = 50
from time import time
accs_train = []
loss_train = []
accs_test = []
loss_test = []
for e in range(epochs):
    start_time = time()
    accs_train,loss_train = train_epoch(net, criterion, optimizer, trainloader,accs_train,loss_train)
    accs_test,loss_test = eval_epoch(net, criterion, valloader,accs_test,loss_test)

    end_time = time()

    print(f'Epoch {e+1:3} finished in {end_time - start_time:.2f}s')

plt.plot(np.array(loss_test), 'r')
plt.plot(np.array(loss_train), 'b')
plt.title('Model loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('loss1.jpg')
plt.show()

plt.plot(np.array(accs_test), 'r')
plt.plot(np.array(accs_train), 'b')
plt.title('Model Accuracy')
plt.ylabel('Accuracy')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('acc1.jpg')
plt.show()

torch.save(net.state_dict(), 'alexNet1.pth')
print(f'Best Accuracy:{max(accs_test) * 100.:.2f}%')

class AlexNet2(nn.Module):
    def __init__(self, num_classes: int = 15, dropout: float = 0.5) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(64, 192, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(192, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(256 * 6 * 6, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(4096, 4096),
            nn.ReLU(inplace=True),
            nn.Linear(4096, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

net = AlexNet2().to(device)
net

criterion = nn.CrossEntropyLoss().to(device)
optimizer = torch.optim.Adam(net.parameters(), lr=1e-4)

epochs = 50
from time import time
accs_train = []
loss_train = []
accs_test = []
loss_test = []
for e in range(epochs):
    start_time = time()
    accs_train,loss_train = train_epoch(net, criterion, optimizer, trainloader,accs_train,loss_train)
    accs_test,loss_test = eval_epoch(net, criterion, valloader,accs_test,loss_test)
    end_time = time()

    print(f'Epoch {e+1:3} finished in {end_time - start_time:.2f}s')

plt.plot(np.array(loss_test), 'r')
plt.plot(np.array(loss_train), 'b')
plt.title('Model loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('loss2.jpg')
plt.show()

plt.plot(np.array(accs_test), 'r')
plt.plot(np.array(accs_train), 'b')
plt.title('Model Accuracy')
plt.ylabel('Accuracy')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('acc2.jpg')
plt.show()

torch.save(net.state_dict(), 'alexNet2.pth')
print(f'Best Accuracy:{max(accs_test) * 100.:.2f}%')

accs = []
class AlexNet3(nn.Module):
    def __init__(self, num_classes: int = 15, dropout: float = 0.5) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(64, 192, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(192, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(384, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
        )
        self.avgpool = nn.AdaptiveAvgPool2d((6, 6))
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(256 * 6 * 6, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(4096, 4096),
            nn.ReLU(inplace=True),
            nn.Linear(4096, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

net = AlexNet3().to(device)
net

criterion = nn.CrossEntropyLoss().to(device)
optimizer = torch.optim.Adam(net.parameters(), lr=1e-4)

epochs = 50
from time import time
accs_train = []
loss_train = []
accs_test = []
loss_test = []
for e in range(epochs):
    start_time = time()
    accs_train,loss_train = train_epoch(net, criterion, optimizer, trainloader,accs_train,loss_train)
    accs_test,loss_test = eval_epoch(net, criterion, valloader,accs_test,loss_test)

    end_time = time()

    print(f'Epoch {e+1:3} finished in {end_time - start_time:.2f}s')

plt.plot(np.array(loss_test), 'r')
plt.plot(np.array(loss_train), 'b')
plt.title('Model loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('loss3.jpg')
plt.show()

plt.plot(np.array(accs_test), 'r')
plt.plot(np.array(accs_train), 'b')
plt.title('Model Accuracy')
plt.ylabel('Accuracy')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('acc3.jpg')
plt.show()

torch.save(net.state_dict(), 'alexNet3.pth')
print(f'Best Accuracy:{max(accs_test) * 100.:.2f}%')

import torch
import torch.nn as nn
try:
    from torch.hub import load_state_dict_from_url
except ImportError:
    from torch.utils.model_zoo import load_url as load_state_dict_from_url

__all__ = ["AlexNet", "alexnet"]


model_urls = {
    "alexnet": "https://download.pytorch.org/models/alexnet-owt-7be5be79.pth",
}

accs = []
class AlexNet4(nn.Module):
    def __init__(self, num_classes: int = 15, dropout: float = 0.5) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(64, 192, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(192, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(384, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
        )
        self.avgpool = nn.AdaptiveAvgPool2d((6, 6))
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(256 * 6 * 6, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(4096, 4096),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

class lastLayer(nn.Module):
    def __init__(self, pretrained):
        super(lastLayer, self).__init__()
        self.pretrained = pretrained
        self.last = nn.Sequential(nn.ReLU(inplace=True),
                                           nn.Linear(4096, 15))
    
    def forward(self, x):
        x = self.pretrained(x)
        x = self.last(x)
        return x


net = AlexNet4()
for param in net.parameters():
      param.requires_grad = False

state_dict = load_state_dict_from_url(model_urls["alexnet"], progress=True)
net.load_state_dict(state_dict,strict=False)
net = lastLayer(net).to(device)

criterion = nn.CrossEntropyLoss().to(device)
optimizer = torch.optim.Adam(net.parameters(), lr=1e-4)

epochs = 50
from time import time
accs_train = []
loss_train = []
accs_test = []
loss_test = []
for e in range(epochs):
    start_time = time()
    accs_train,loss_train = train_epoch(net, criterion, optimizer, trainloader,accs_train,loss_train)
    accs_test,loss_test = eval_epoch(net, criterion, valloader,accs_test,loss_test)

    end_time = time()

    print(f'Epoch {e+1:3} finished in {end_time - start_time:.2f}s')

plt.plot(np.array(loss_test), 'r')
plt.plot(np.array(loss_train), 'b')
plt.title('Model loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('loss4.jpg')
plt.show()

plt.plot(np.array(accs_test), 'r')
plt.plot(np.array(accs_train), 'b')
plt.title('Model Accuracy')
plt.ylabel('Accuracy')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('acc4.jpg')
plt.show()

torch.save(net.state_dict(), 'alexNet4.pth')
print(f'Best Accuracy:{max(accs_test) * 100.:.2f}%')

accs = []
class AlexNet5(nn.Module):
    def __init__(self, num_classes: int = 15, dropout: float = 0.5) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(64, 192, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(192, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(384, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
        )
        self.avgpool = nn.AdaptiveAvgPool2d((6, 6))
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(256 * 6 * 6, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(4096, 4096),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

class lastLayer(nn.Module):
    def __init__(self, pretrained):
        super(lastLayer, self).__init__()
        self.pretrained = pretrained
        self.last = nn.Sequential(nn.ReLU(inplace=True),
                                           nn.Linear(4096, 15))
    
    def forward(self, x):
        x = self.pretrained(x)
        x = self.last(x)
        return x


net = AlexNet5()


state_dict = load_state_dict_from_url(model_urls["alexnet"], progress=True)
net.load_state_dict(state_dict,strict=False)
net = lastLayer(net).to(device)

criterion = nn.CrossEntropyLoss().to(device)
optimizer = torch.optim.Adam(net.parameters(), lr=1e-4)


epochs = 50
from time import time
accs_train = []
loss_train = []
accs_test = []
loss_test = []
for e in range(epochs):
    start_time = time()
    accs_train,loss_train = train_epoch(net, criterion, optimizer, trainloader,accs_train,loss_train)
    accs_test,loss_test = eval_epoch(net, criterion, valloader,accs_test,loss_test)

    end_time = time()

    print(f'Epoch {e+1:3} finished in {end_time - start_time:.2f}s')

plt.plot(np.array(loss_test), 'r')
plt.plot(np.array(loss_train), 'b')
plt.title('Model loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('loss5.jpg')
plt.show()

plt.plot(np.array(accs_test), 'r')
plt.plot(np.array(accs_train), 'b')
plt.title('Model Accuracy')
plt.ylabel('Accuracy')
plt.xlabel('Epoch')
plt.legend(['Test', 'Train'])
plt.savefig('acc5.jpg')
plt.show()

torch.save(net.state_dict(), 'alexNet5.pth')
print(f'Best Accuracy:{max(accs_test) * 100.:.2f}%')