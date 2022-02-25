# Paper review (in progress)

This repo seeks to understand what is happening in deep learning architectures 
from a paper at a very granular level.

My goal is to pull apart the architecture to understand what each piece does
and how it contributes to the success of the architecture. By doing this
I hope to increase my own understanding of computer vision, DL architectures
and DL broadly.

I'm exploring the techniques in this paper whilst continuing research into 
using deep learning techniques to estimate tree density using UAV/satellite
images.

The paper this repo is based on is: **Adaptive Mixture Regression Network with 
Local Counting Map for Crowd Counting** by Xiyang Liu, Jie Yang and Wenrui Ding

## Links
* [Papers with code](https://paperswithcode.com/paper/adaptive-mixture-regression-network-with)
* [Arxiv](https://arxiv.org/pdf/2005.05776v2.pdf)
* [GitHub](https://github.com/xiyang1012/Local-Crowd-Counting)

## Contents
**Note**: test_classes.Summary and test_classes.CvTest are custom tools I've built, I will make the code for these available on 
  github in the coming weeks
* **amr_vgg16_lcm_reg_exploration.ipynb**
  * This looks at the model file VGG16_LCM_REG.py in depth, in particular exploring 
    the step by step processes involved in the Mixture Regression Module (MRM)
  * Exploration of some DL theory
    * Activation functions
    * 1x1 convolution
* **amr_vgg16_lcm_reg_rebuild.ipynb**
  * Step by step analysis of model outputs, exploration of effects
* **tree_results_vgg16_lcm_reg.ipynb**
  * Results of experiment when applying vgg16_lcm_reg model to london tree dataset
* test_config.py
  * config file copied from repo to be able to run the code in model file



## Todo
* Indepth explortation of model file ResNet_LCM_v2.py
* Step by step dissection of model outputs
* Application to and measured performance on [london-trees-dataset](https://github.com/cormac-rynne/london-trees-dataset)
  for a range of off-the-shelf models (CSRNet, VGG16, ResNet etc) and comparison with the various 
  LCM models in this paper
