from __future__ import absolute_import, print_function

from collections import OrderedDict

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models
from test_config import cfg
import os
import numpy as np

from logger import logger
logger = logger(__name__)

data_mode = cfg.DATASET
if data_mode == 'SHHA':
    patch_max = cfg.SHHAPATCHMAX
elif data_mode == 'SHHB':
    patch_max = cfg.SHHBPATCHMAX
elif data_mode == 'QNRF':
    patch_max = cfg.QNRFPATCHMAX
elif data_mode == 'UCF50':
    patch_max = cfg.CC50PATCHMAX
elif data_mode == 'london':
    patch_max = cfg.LONDONPATCHMAX

def log_output(var_name, var):
    logger.info(f'{var_name}: {var.shape}')
    np.save(f'./model_outputs/{var_name}.npy', var.cpu().numpy())

class VGG16_LCM_REG(nn.Module):
    def __init__(self, load_weights=False, stage_num=[3,3,3], count_range=patch_max, lambda_i=1., lambda_k=1.):
        super(VGG16_LCM_REG, self).__init__()
        logger.info('===PAPER REVIEW VERSION===')

        # cfg
        self.stage_num = stage_num
        self.lambda_i = lambda_i
        self.lambda_k = lambda_k
        self.count_range = count_range
        self.multi_fuse = True
        self.soft_interval = True

        self.layer3 = self.VGG_make_layers([64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512])
        self.layer4 = self.VGG_make_layers(['M', 512, 512, 512], in_channels=512)
        self.layer5 = self.VGG_make_layers(['M', 512, 512, 512], in_channels=512)

        if self.multi_fuse:
            self.fuse_layer5 = DC_layer(level=0)
            self.fuse_layer4 = DC_layer(level=1)
            self.fuse_layer3 = DC_layer(level=2)

        self.count_layer5 = Count_layer(pool=2)
        self.count_layer4 = Count_layer(pool=4)
        self.count_layer3 = Count_layer(pool=8)
        
        if self.soft_interval:
            """
            layer_k tanh
            layer_i sigmoid
            """
            self.layer5_k = nn.Sequential(
                nn.Conv2d(512, 1, kernel_size=1),
                nn.Tanh(),
            )
            self.layer4_k = nn.Sequential(
                nn.Conv2d(512, 1, kernel_size=1),
                nn.Tanh(),
            )
            self.layer3_k = nn.Sequential(
                nn.Conv2d(512, 1, kernel_size=1),
                nn.Tanh(),
            )
        
            self.layer5_i = nn.Sequential(
                nn.Conv2d(512, self.stage_num[0], kernel_size=1),
                nn.Sigmoid(),
            )
            self.layer4_i = nn.Sequential(
                nn.Conv2d(512, self.stage_num[1], kernel_size=1),
                nn.Sigmoid(),
            )
            self.layer3_i = nn.Sequential(
                nn.Conv2d(512, self.stage_num[2], kernel_size=1),
                nn.Sigmoid(),
            )

        # layers p relu
        self.layer5_p = nn.Sequential(
            nn.Conv2d(512, self.stage_num[0], kernel_size=1),
            nn.ReLU(),
        )
        self.layer4_p = nn.Sequential(
            nn.Conv2d(512, self.stage_num[1], kernel_size=1),
            nn.ReLU(),
        )
        self.layer3_p = nn.Sequential(
            nn.Conv2d(512, self.stage_num[2], kernel_size=1),
            nn.ReLU(),
        )

        if load_weights:
            #self._initialize_weights()

            mod = models.vgg16(pretrained=True)

            new_state_dict = OrderedDict()
            for key, params in mod.features[0:23].state_dict().items():
                new_state_dict[key] = params
            self.layer3.load_state_dict(new_state_dict)

            new_state_dict = OrderedDict()
            for key, params in mod.features[23:30].state_dict().items():
                key = str(int(key[:2]) - 23) + key[2:]
                new_state_dict[key] = params
            self.layer4.load_state_dict(new_state_dict)

            new_state_dict = OrderedDict()
            for key, params in mod.features[23:30].state_dict().items():
                key = str(int(key[:2]) - 23) + key[2:]
                new_state_dict[key] = params
            self.layer5.load_state_dict(new_state_dict)

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.normal_(m.weight, std=0.01)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        
        x3 = self.layer3(x)
        log_output('x3', x3)

        # np.save('./model_outputs/x3.npy', x3.cpu().numpy())
        x4 = self.layer4(x3)
        log_output('x4', x4)

        x5 = self.layer5(x4)
        log_output('x5', x5)

        if self.multi_fuse:
            x5 = self.fuse_layer5(x5)
            log_output('multifuse_x5', x5)

            x4 = self.fuse_layer4(x4)
            log_output('multifuse_x4', x4)

            x3 = self.fuse_layer3(x3)
            log_output('multifuse_x3', x3)

        x5_= self.count_layer5(x5)
        log_output('countlayer_x4_', x5_)

        p5 = self.layer5_p(x5_)
        log_output('p5', p5)

        if self.soft_interval:
            k5 = self.layer5_k(x5_)
            log_output('k5', k5)

            i5 = self.layer5_i(x5_)
            log_output('i5', i5)

        x4_ = self.count_layer4(x4)
        log_output('countlayer_x4_', x4_)

        p4 = self.layer4_p(x4_)
        log_output('p4', p4)

        if self.soft_interval:
            k4 = self.layer4_k(x4_)
            log_output('k4', k4)
            i4 = self.layer4_i(x4_)
            log_output('i4', i4)

        x3_ = self.count_layer3(x3)
        log_output('countlayer_x3_', x3_)
        p3 = self.layer3_p(x3_)
        log_output('p3', p3)
        if self.soft_interval:
            k3 = self.layer3_k(x3_)
            log_output('k3', k3)
            i3 = self.layer3_i(x3_)
            log_output('i3', i3)

        stage1_regress = p5[:, 0, :, :] * 0
        log_output('stage1_regress0', stage1_regress)
        stage2_regress = p4[:, 0, :, :] * 0
        log_output('stage2_regress0', stage1_regress)
        stage3_regress = p3[:, 0, :, :] * 0
        log_output('stage3_regress0', stage1_regress)


        for index in range(self.stage_num[0]):
            if self.soft_interval:
                stage1_regress = stage1_regress + (float(index) + self.lambda_i * i5[:, index, :, :]) * p5[:, index, :, :]
            else:
                stage1_regress = stage1_regress + float(index) * p5[:, index, :, :]
            log_output(f'stage1_regress1_{index}', stage1_regress)

        stage1_regress = torch.unsqueeze(stage1_regress, 1)
        log_output(f'stage1_regress2', stage1_regress)

        if self.soft_interval:
            stage1_regress = stage1_regress / ( float(self.stage_num[0]) * (1. + self.lambda_k * k5) )
        else:
            stage1_regress = stage1_regress / float(self.stage_num[0])
        log_output(f'stage1_regress3_{index}', stage1_regress)


        for index in range(self.stage_num[1]):
            if self.soft_interval:
                stage2_regress = stage2_regress + (float(index) + self.lambda_i * i4[:, index, :, :]) * p4[:, index, :, :]
            else:
                stage2_regress = stage2_regress + float(index) * p4[:, index, :, :]
            log_output(f'stage2_regress1_{index}', stage2_regress)
        stage2_regress = torch.unsqueeze(stage2_regress, 1)
        log_output(f'stage2_regress2_{index}', stage2_regress)
        if self.soft_interval:
            stage2_regress = stage2_regress / ( (float(self.stage_num[0]) * (1. + self.lambda_k * k5)) *
                                                (float(self.stage_num[1]) * (1. + self.lambda_k * k4)) )
        else:
            stage2_regress = stage2_regress / float( self.stage_num[0] * self.stage_num[1] )
        log_output(f'stage2_regress3', stage2_regress)

        for index in range(self.stage_num[2]):
            if self.soft_interval:
                stage3_regress = stage3_regress + (float(index) + self.lambda_i * i3[:, index, :, :]) * p3[:, index, :, :]
            else:
                stage3_regress = stage3_regress + float(index) * p3[:, index, :, :]
            log_output(f'stage3_regress1_{index}', stage3_regress)
        stage3_regress = torch.unsqueeze(stage3_regress, 1)
        log_output(f'stage3_regress2_{index}', stage3_regress)
        if self.soft_interval:
            stage3_regress = stage3_regress / ( (float(self.stage_num[0]) * (1. + self.lambda_k * k5)) *
                                                (float(self.stage_num[1]) * (1. + self.lambda_k * k4)) *
                                                (float(self.stage_num[2]) * (1. + self.lambda_k * k3)) )
        else:
            stage3_regress = stage3_regress / float( self.stage_num[0] * self.stage_num[1] * self.stage_num[2] )
        log_output(f'stage3_regress3', stage3_regress)

        # regress_count = stage1_regress * self.count_range
        # regress_count = (stage1_regress + stage2_regress) * self.count_range
        regress_count = (stage1_regress + stage2_regress + stage3_regress) * self.count_range

        return regress_count

    def VGG_make_layers(self, cfg, in_channels=3, batch_norm=False, dilation=1):
        d_rate = dilation
        layers = []
        for v in cfg:
            if v == 'M':
                layers += [nn.MaxPool2d(kernel_size=2, stride=2)]
            else:
                conv2d = nn.Conv2d(in_channels, v, kernel_size=3, padding=d_rate, dilation=d_rate)
                if batch_norm:
                    layers += [conv2d, nn.BatchNorm2d(v), nn.ReLU(inplace=True)]
                else:
                    layers += [conv2d, nn.ReLU(inplace=True)]
                in_channels = v
        return nn.Sequential(*layers)


class Count_layer(nn.Module):
    """
    Avg pool, max pool, concat
    1x1 conv/merge concatenated layer
    """
    def __init__(self, inplanes=512, pool=2):
        super(Count_layer, self).__init__()
        self.avgpool_layer = nn.Sequential(
            nn.Conv2d(inplanes, inplanes, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.AvgPool2d((pool, pool), stride=pool),
        )
        self.maxpool_layer = nn.Sequential(
            nn.Conv2d(inplanes, inplanes, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((pool, pool), stride=pool),
        )
        self.conv1x1= nn.Sequential(
            nn.Conv2d(inplanes*2, inplanes, kernel_size=1),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        x_avg = self.avgpool_layer(x)
        x_max = self.maxpool_layer(x)

        x = torch.cat([x_avg, x_max], dim=1)
        x = self.conv1x1(x)
        return x


class DC_layer(nn.Module):
    """
    Direct counting layer


    """
    def __init__(self, level, fuse=False):
        super(DC_layer, self).__init__()
        self.level = level
        self.conv1x1_d1 = nn.Conv2d(512, 512, kernel_size=1)
        self.conv1x1_d2 = nn.Conv2d(512, 512, kernel_size=1)
        self.conv1x1_d3 = nn.Conv2d(512, 512, kernel_size=1)
        self.conv1x1_d4 = nn.Conv2d(512, 512, kernel_size=1)

        self.conv_d1 = nn.Conv2d(512, 512, kernel_size=3, padding=1, dilation=1)
        self.conv_d2 = nn.Conv2d(512, 512, kernel_size=3, padding=2, dilation=2)
        self.conv_d3 = nn.Conv2d(512, 512, kernel_size=3, padding=3, dilation=3)
        self.conv_d4 = nn.Conv2d(512, 512, kernel_size=3, padding=4, dilation=4)
        
        self.fuse = fuse
        if self.fuse:
            self.fuse = nn.Conv2d(512*2, 512, kernel_size=3, padding=1)
            self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        x1 = self.conv1x1_d1(x)
        x2 = self.conv1x1_d2(x)
        x3 = self.conv1x1_d3(x)
        x4 = self.conv1x1_d4(x)

        x1 = self.conv_d1(x1)
        x2 = self.conv_d2(x2)
        x3 = self.conv_d3(x3)
        x4 = self.conv_d4(x4)

        # x = torch.cat([x1, x2, x3, x4], dim=1)
        # x = self.relu(self.fuse(x))
        x = Maxout(x1, x2, x3, x4)
        return x

def Maxout(x1, x2, x3, x4):
    """

    Args:
        x1:
        x2:
        x3:
        x4:

    Returns:

    """

    # mask for x1 >= x2
    mask_1 = torch.ge(x1, x2)
    mask_1 = mask_1.float()
    x = mask_1 * x1 + (1-mask_1) * x2

    mask_2 = torch.ge(x, x3)
    mask_2 = mask_2.float()
    x = mask_2 * x + (1-mask_2) * x3

    mask_3 = torch.ge(x, x4)
    mask_3 = mask_3.float()
    x = mask_3 * x + (1-mask_3) * x4
    return x


if __name__ == "__main__":
    model = VGG16_LCM_REG(load_weights=False)

    model.eval()
    image = torch.randn(2, 3, 384, 384)
    x5, c = model(image)
    # print(model)
    print("input:", image.shape)
    # print("x5:", x5.shape)
    print("c:", c.shape)
