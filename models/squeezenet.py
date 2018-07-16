"""
    SqueezeNet, implemented in Gluon.
    Original paper: 'SqueezeNet: AlexNet-level accuracy with 50x fewer parameters and <0.5MB model size'
"""

from mxnet import cpu
from mxnet.gluon import nn, HybridBlock


class FireConv(HybridBlock):

    def __init__(self,
                 in_channels,
                 out_channels,
                 kernel_size,
                 padding,
                 **kwargs):
        super(FireConv, self).__init__(**kwargs)
        with self.name_scope():
            self.conv = nn.Conv2D(
                channels=out_channels,
                kernel_size=kernel_size,
                padding=padding,
                in_channels=in_channels)
            self.activ = nn.Activation('relu')

    def hybrid_forward(self, F, x):
        x = self.conv(x)
        x = self.activ(x)
        return x


class FireUnit(HybridBlock):

    def __init__(self,
                 in_channels,
                 squeeze_channels,
                 expand1x1_channels,
                 expand3x3_channels,
                 **kwargs):
        super(FireUnit, self).__init__(**kwargs)
        with self.name_scope():
            self.squeeze = FireConv(
                in_channels=in_channels,
                out_channels=squeeze_channels,
                kernel_size=1,
                padding=0)
            self.expand1x1 = FireConv(
                in_channels=squeeze_channels,
                out_channels=expand1x1_channels,
                kernel_size=1,
                padding=0)
            self.expand3x3 = FireConv(
                in_channels=squeeze_channels,
                out_channels=expand3x3_channels,
                kernel_size=3,
                padding=1)

    def hybrid_forward(self, F, x):
        x = self.squeeze(x)
        y1 = self.expand1x1(x)
        y2 = self.expand3x3(x)
        out = F.concat(y1, y2, dim=1)
        return out


def squeeze_pool():
    return nn.MaxPool2D(
        pool_size=3,
        strides=2,
        ceil_mode=True)


class SqueezeInitBlock(HybridBlock):

    def __init__(self,
                 in_channels,
                 out_channels,
                 kernel_size):
        super(SqueezeInitBlock, self).__init__()
        with self.name_scope():
            self.conv = nn.Conv2D(
                channels=out_channels,
                kernel_size=kernel_size,
                strides=2,
                in_channels=in_channels)
            self.activ = nn.Activation('relu')

    def hybrid_forward(self, F, x):
        x = self.conv(x)
        x = self.activ(x)
        return x


class SqueezeNet(HybridBlock):

    def __init__(self,
                 first_out_channels,
                 first_kernel_size,
                 pool_stages,
                 classes=1000,
                 **kwargs):
        super(SqueezeNet, self).__init__(**kwargs)
        input_channels = 3
        stage_squeeze_channels = [16, 32, 48, 64]
        stage_expand_channels = [64, 128, 192, 256]

        with self.name_scope():
            self.features = nn.HybridSequential(prefix='')
            self.features.add(SqueezeInitBlock(
                in_channels=input_channels,
                out_channels=first_out_channels,
                kernel_size=first_kernel_size))
            k = 0
            pool_ind = 0
            for i in range(len(stage_squeeze_channels)):
                for j in range(2):
                    if (pool_ind < len(pool_stages) - 1) and (k == pool_stages[pool_ind]):
                        self.features.add(squeeze_pool())
                        pool_ind += 1
                    in_channels = first_out_channels if (i == 0 and j == 0) else \
                        (2 * stage_expand_channels[i - 1] if j == 0 else 2 * stage_expand_channels[i])
                    self.features.add(FireUnit(
                        in_channels=in_channels,
                        squeeze_channels=stage_squeeze_channels[i],
                        expand1x1_channels=stage_expand_channels[i],
                        expand3x3_channels=stage_expand_channels[i]))
                    k += 1
            self.features.add(nn.Dropout(0.5))

            self.output = nn.HybridSequential(prefix='')
            self.output.add(nn.Conv2D(classes, kernel_size=1))
            self.output.add(nn.Activation('relu'))
            self.output.add(nn.AvgPool2D(13))
            self.output.add(nn.Flatten())

    def hybrid_forward(self, F, x):
        x = self.features(x)
        x = self.output(x)
        return x


def get_squeezenet(version,
                      pretrained=False,
                      ctx=cpu(),
                      **kwargs):
    if version == '1.0':
        first_out_channels = 96
        first_kernel_size = 7
        pool_stages = [0, 3, 7]
    elif version == '1.1':
        first_out_channels = 64
        first_kernel_size = 3
        pool_stages = [0, 2, 4]
    else:
        raise ValueError("Unsupported SqueezeNet version {}: 1.0 or 1.1 expected".format(version))

    return SqueezeNet(
        first_out_channels=first_out_channels,
        first_kernel_size=first_kernel_size,
        pool_stages=pool_stages,
        **kwargs)


def squeezenet1_0(**kwargs):
    return get_squeezenet('1.0', **kwargs)


def squeezenet1_1(**kwargs):
    return get_squeezenet('1.1', **kwargs)

