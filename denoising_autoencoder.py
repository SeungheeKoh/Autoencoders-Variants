import warnings
warnings.filterwarnings('ignore')
import os, datetime
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

import torch
import torchvision
import data_utils
import matplotlib.pyplot as plt

from torch import nn
from torch.autograd import Variable

from simple_autoencoder import Autoencoder

cuda = torch.cuda.is_available()
device = torch.device('cuda:0' if cuda else 'cpu')

def noise_input(images):
    return images * (1 - NOISE_RATIO) + torch.rand(images.size()) * NOISE_RATIO

def model_training(autoencoder, train_loader, epoch):
    loss_metric = nn.MSELoss()
    optimizer = torch.optim.Adam(autoencoder.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)

    autoencoder.train()
    for i, data in enumerate(train_loader):
        optimizer.zero_grad()
        images, _ = data
        images = Variable(images)
        images = images.view(images.size(0), -1)
        noise_images = noise_input(images)      # add noise into image data
        if cuda: images, noise_images = images.to(device), noise_images.to(device)
        outputs = autoencoder(noise_images)
        loss = loss_metric(outputs, images)
        loss.backward()
        optimizer.step()
        if (i + 1) % LOG_INTERVAL == 0:
            print('Epoch [{}/{}] - Iter[{}/{}], MSE loss:{:.4f}'.format(
                epoch + 1, EPOCHS, i + 1, len(train_loader.dataset) // BATCH_SIZE, loss.item()
            ))


def evaluation(autoencoder, test_loader):
    total_loss = 0
    loss_metric = nn.MSELoss()
    autoencoder.eval()
    for i, data in enumerate(test_loader):
        images, _ = data
        images = Variable(images)
        images = images.view(images.size(0), -1)
        if cuda: images = images.to(device)
        outputs = autoencoder(images)
        loss = loss_metric(outputs, images)
        total_loss += loss * len(images)
    avg_loss = total_loss / len(test_loader.dataset)

    print('\nAverage MSE Loss on Test set: {:.4f}'.format(avg_loss))

    global BEST_VAL
    if TRAIN_SCRATCH and avg_loss < BEST_VAL:
        BEST_VAL = avg_loss
        torch.save(autoencoder.state_dict(), './history/denoise_autoencoder.pt')
        print('Save Best Model in HISTORY\n')

if __name__ == '__main__':

    EPOCHS = 100
    BATCH_SIZE = 128
    LEARNING_RATE = 1e-3
    WEIGHT_DECAY = 1e-5
    LOG_INTERVAL = 100
    NOISE_RATIO = 0.4
    TRAIN_SCRATCH = False        # whether to train a model from scratch
    BEST_VAL = float('inf')     # record the best val loss

    train_loader, test_loader = data_utils.load_mnist(BATCH_SIZE)

    autoencoder = Autoencoder()
    if cuda: autoencoder.to(device)

    if TRAIN_SCRATCH:
        # Training autoencoder from scratch
        for epoch in range(EPOCHS):
            starttime = datetime.datetime.now()
            model_training(autoencoder, train_loader, epoch)
            endtime = datetime.datetime.now()
            print(f'Train a epoch in {(endtime - starttime).seconds} seconds')
            # evaluate on test set and save best model
            evaluation(autoencoder, test_loader)
        print('Trainig Complete with best validation loss {:.4f}'.format(BEST_VAL))

    else:
        autoencoder.load_state_dict(torch.load('./history/denoise_autoencoder.pt'))
        evaluation(autoencoder, test_loader)

        autoencoder.cpu()
        dataiter = iter(train_loader)
        images, _ = next(dataiter)
        images = Variable(images[:32])

        noise_images = noise_input(images)
        outputs = autoencoder(noise_images.view(images.size(0), -1))

        # plot and save original and reconstruction images for comparisons
        plt.figure(figsize=(10, 5))
        plt.subplot(131)
        plt.title('MNIST Images')
        data_utils.imshow(torchvision.utils.make_grid(images))
        plt.subplot(132)
        plt.title('Noise Images')
        data_utils.imshow(torchvision.utils.make_grid(noise_images))
        plt.subplot(133)
        plt.title('Autoencoder Reconstruction')
        data_utils.imshow(torchvision.utils.make_grid(
            outputs.view(images.size(0), 1, 28, 28).data
        ))
        plt.savefig('./images/denoise_autoencoder.png')
