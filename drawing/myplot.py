from tensorboard.backend.event_processing import event_accumulator
import matplotlib.pyplot as plt
import os
import numpy as np
import torch
from parameter import NN_SIZE
from module import Module
import scipy.io
from matplotlib.colors import Normalize
from scipy.interpolate import griddata
from matplotlib.colorbar import Colorbar

numerical_data = scipy.io.loadmat('../data/Cylinder2D_Re200Pec2000_Neumann_Streaks.mat')
x = numerical_data['x_data'][:, 0]  # N x 1
y = numerical_data['y_data'][:, 0]  # N x 1
U_star = numerical_data['U_data']  # N x T
V_star = numerical_data['V_data']  # N x T
P_star = numerical_data['P_data']  # N x T
C_star = numerical_data['C_data']  # N x T
t_x_y = np.zeros((len(x), 3))

t_x_y[:, 0] = 8
t_x_y[:, 1] = x
t_x_y[:, 2] = y

# loc_num = ['0', '8', '10', '12', '14', '16']
loc_num = ['1', '2', '3', '4', '5', '6']


def read_file(path):
    for root, dirs, files in os.walk(path):
        return dirs


def read_tensorboard(path):  # path为tensoboard文件的路径
    ea = event_accumulator.EventAccumulator(path)  # 初始化EventAccumulator对象
    ea.Reload()  # 将事件的内容都导进去
    return ea.scalars.Items(ea.scalars.Keys()[0])


def residual_plot(ax, path, idx):
    out = read_model(path)[:, idx]
    c = [C_star, U_star, V_star, P_star][idx+1]
    c = c[:, 100]
    res = out - c

    dxs = np.linspace(-2.5, 7.5, 1000)
    dys = np.linspace(-2.5, 2.5, 500)
    dxs, dys = np.meshgrid(dxs, dys)
    z_new = griddata((x, y), res, (dxs, dys), method='linear')

    norm = Normalize(vmin=-2, vmax=2)

    ax.imshow(z_new, cmap=plt.get_cmap('seismic'), norm=norm)


def read_model(path):
    NN = Module([3] + 5 * [2 * 50] + [3])

    if os.path.exists(path):
        state = torch.load(path, map_location=torch.device('cpu'))

        NN.load_state_dict(state['model'])
        print('load success')

    return NN(torch.FloatTensor(t_x_y)).detach().numpy()


def read_tbs(path):
    loss = []
    loss_1, loss_2, loss_3, loss_4 = [], [], [], []
    for num in loc_num:
        p1 = path + num + '/les'
        p2 = path + num + '/ns'

        names1 = read_file(p1)
        names2 = read_file(p2)
        datas1 = {}
        datas2 = {}
        print(names1, names2)
        for name in names1:
            log = read_tensorboard(p1 + '/' + name)
            datas1[name] = np.array([[i.step, i.value] for i in log])
        for name in names2:
            log = read_tensorboard(p2 + '/' + name)
            datas2[name] = np.array([[i.step, i.value] for i in log])

        l = np.mean(datas1['validation_loss_total'][-500:-1, 1])
        # l1 = np.mean(datas1['validation_loss_c'][-500:-1, 1])
        l1 = np.mean(datas1['validation_loss_u'][-500:-1, 1])
        l2 = np.mean(datas1['validation_loss_v'][-500:-1, 1])
        l3 = np.mean(datas1['validation_loss_p'][-500:-1, 1])

        n = np.mean(datas2['validation_loss_total'][-500:-1, 1])
        # n1 = np.mean(datas2['ns_validation_loss_c'][-500:-1, 1])
        n1 = np.mean(datas2['validation_loss_u'][-500:-1, 1])
        n2 = np.mean(datas2['validation_loss_v'][-500:-1, 1])
        n3 = np.mean(datas2['validation_loss_p'][-500:-1, 1])

        loss.append([l, n])
        loss_1.append([l1, n1])
        loss_2.append([l2, n2])
        loss_3.append([l3, n3])
        # loss_4.append([l4, n4])

    np.savez('data.npz', total=loss, u=loss_1, v=loss_2, p=loss_3)


def bar_lin(path, x_label):
    npz_data = np.load(path)
    bar_data_1 = npz_data['total'][:, 0]
    bar_data_2 = npz_data['total'][:, 1]
    # bar_data_1[-1] = 0.04
    # lin_data_c = npz_data['c']
    lin_data_u = npz_data['u']
    lin_data_v = npz_data['v']
    lin_data_p = npz_data['p']

    x = np.arange(len(bar_data_1))
    width = 0.3
    x1 = x - width / 2
    x2 = x + width / 2

    fig = plt.figure(figsize=(12, 9))
    ax1 = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    ax1.bar(x1, bar_data_1, width=width, label='les loss', color='gray')
    ax1.bar(x2, bar_data_2, width=width, label='ns loss', color='black')
    ax1.set_xlabel('Sampling ratio')
    ax1.set_ylabel('')
    plt.xticks(x, x_label)

    # ax2 = plt.twinx()
    # ax2.set_ylim([-0.003, 0.05])
    #
    # ax2.plot(x1, lin_data_c[:, 0], marker='o', c='g', label='c loss', markersize=10, alpha=0.6)
    # ax2.plot(x2, lin_data_c[:, 1], marker='o', ls=':', c='g', markersize=10, alpha=0.6)
    # ax2.plot(x1, lin_data_u[:, 0], marker='o', c='r', label='u loss', markersize=10, alpha=0.6)
    # ax2.plot(x2, lin_data_u[:, 1], marker='o', ls=':', c='r', markersize=10, alpha=0.6)
    # ax2.plot(x1, lin_data_v[:, 0], marker='o', c='b', label='v loss', markersize=10, alpha=0.6)
    # ax2.plot(x2, lin_data_v[:, 1], marker='o', ls=':', c='b', markersize=10, alpha=0.6)
    # ax2.plot(x1, lin_data_p[:, 0], marker='o', c='orange', label='p loss', markersize=10, alpha=0.6)
    # ax2.plot(x2, lin_data_p[:, 1], marker='o', ls=':', c='orange', markersize=10, alpha=0.6)

    sub_img(fig, [[0.12, 0.55, 0.13, 0.1],
                  [0.27, 0.45, 0.13, 0.1],
                  [0.41, 0.6, 0.13, 0.1],
                  [0.55, 0.45, 0.13, 0.1],
                  [0.56, 0.7, 0.13, 0.1],
                  [0.72, 0.7, 0.13, 0.1]])

    ax_c = fig.add_axes([0.3, 0.65, 0.01, 0.15])
    ax_c.set_title('Res color bar\nup / down: les / ns model')
    Colorbar(ax_c, plt.cm.ScalarMappable(norm=Normalize(vmin=-2, vmax=2), cmap="seismic"))

    fig.legend(bbox_to_anchor=(0.2, 0.9))
    plt.show()


def sub_img(figure, loc):
    name = loc_num
    idx = [0, 1, 2, 0, 1, 2]
    for i, l, n in zip(idx, loc, name):
        # i = 1
        ax1 = figure.add_axes(l)
        a = ['U', 'V', 'P'][i]
        ax1.set_title(a + "'s residual 1/2^" + n)
        residual_plot(ax1, '/Users/jonathan/Downloads/train_history/noisy/' + n + '/les/Cylinder', i)
        ax1.set_xticks([])
        ax1.set_yticks([])
        cylinder = plt.Circle(xy=(250, 250), radius=50, alpha=1, color='black')
        ax1.add_patch(cylinder)

        l[1] = l[1] - l[3]
        ax2 = figure.add_axes(l)
        residual_plot(ax2, '/Users/jonathan/Downloads/train_history/noisy/' + n + '/ns/Cylinder_rec', i)
        ax2.set_xticks([])
        ax2.set_yticks([])
        cylinder = plt.Circle(xy=(250, 250), radius=50, alpha=1, color='black')
        ax2.add_patch(cylinder)

    # ax.set_colorbar()
    #


if __name__ == '__main__':
    # read_tbs('/Users/jonathan/Downloads/train_history/noisy/')
    bar_lin('data.npz', ['1/4', '1/2', '3/4', '1', '5/4', '3/2'])
    # log = read_tensorboard('../train_history/sparse/0/ns/validation_loss_total')
    # a = np.array([[i.step, i.value] for i in log])
    # plt.plot(a[9000:9998, 0], a[9000:9998, 1])
    # plt.show()
    # path = 'history/sparse/'
    #
    # read_tbs(path)

    pass
