import os
import torch
from condition import loss_pde, loss_data, loss_les, loss_icbc, loss_collcation, x_star, y_star
from num_3d import rare_dataloader_2 as dataloader
from num_3d import validation_data, validation_label
from module import Module
from parameter import NN_SIZE, module_name, device, EPOCH, LOSS, sparse_num, LR, ITERATION
from plt2img import fig2data
import numpy as np

from torch.utils.tensorboard import SummaryWriter

load = False
store = True
torch.manual_seed(3407)
# sparse_num = 'pure'
path = 'train_history/sparse/' + str(sparse_num) + '/ns'
module_name = path + '/' + module_name

if __name__ == '__main__':
    print(device)
    NN = Module(NN_SIZE).to(device)
    opt = torch.optim.SGD(params=NN.parameters(), lr=5e-2)

    start_epoch = 0

    writer = SummaryWriter(path)

    if os.path.exists(module_name + '_les_rec') and load:
        state = torch.load(module_name + '_les_rec')

        NN.load_state_dict(state['model'])
        opt.load_state_dict(state['optimizer'])
        start_epoch = state['epoch']

        print('Start from epoch = %d' % start_epoch)

    min_loss = 1e6
    iter = 0
    x_grid, y_grid = x_star[:, 0], y_star[:, 0]
    t_x_y_grid = np.zeros((x_grid.shape[0], 3))
    t_x_y_grid[:, 0] = 8
    t_x_y_grid[:, 1] = x_grid
    t_x_y_grid[:, 2] = y_grid
    t_x_y_grid = torch.FloatTensor(t_x_y_grid).to(device)

    # tensorboard --logdir=/Users/jonathan/Documents/PycharmProjects/cylinder_flow/train_history --port 14514

    for epoch in range(start_epoch, EPOCH):
        for t_x_y, num_solution in dataloader:
            t_x_y = t_x_y.requires_grad_(True).to(device)
            num_solution = num_solution.requires_grad_(True).to(device)
            opt.zero_grad()
            iter += 1

            # index = torch.LongTensor(np.random.choice(collocation_size, BATCH, replace=False))
            # t_x_y_col = torch.index_select(collocation_points, 0, index)

            loss_u, loss_v, loss_div = loss_pde(NN, t_x_y)  # + loss_les(NN_les, t_x_y_col)
            # c_loss_u, c_loss_v, c_loss_div = loss_collcation(NN, 25 * BATCH, 'ns')
            pde_loss = loss_u + loss_v + loss_div  # + c_loss_u + c_loss_v + c_loss_div

            data_loss_1, data_loss_2 = loss_data(NN, t_x_y, num_solution)
            data_loss = data_loss_1 + data_loss_2

            ic_loss, bc_loss = loss_icbc(NN)
            icbc_loss = ic_loss + bc_loss

            # pde_loss_c, pde_loss_u, pde_loss_v, pde_loss_div = loss_pde(NN_ns, t_x_y)
            # pde_loss = pde_loss_c + pde_loss_u + pde_loss_v + pde_loss_div
            # data_loss_2 = loss_data(NN_ns, t_x_y, num_solution)

            loss = data_loss + pde_loss + icbc_loss
            # loss_2 = data_loss_2 + pde_loss

            validation_out = NN(validation_data)
            [va_u, va_v, va_p] = [LOSS(validation_out[:, 0], validation_label[:, 0]) / 3,
                                  LOSS(validation_out[:, 1], validation_label[:, 1]) / 3,
                                  LOSS(validation_out[:, 2], validation_label[:, 2]) / 3]

            # ns_validation_out = NN_ns(validation_data)
            # [ns_c, ns_u, ns_v, ns_p] = [LOSS(ns_validation_out[:, 0], validation_label[:, 0]) / 4,
            #                             LOSS(ns_validation_out[:, 1], validation_label[:, 1]) / 4,
            #                             LOSS(ns_validation_out[:, 2], validation_label[:, 2]) / 4,
            #                             LOSS(ns_validation_out[:, 3], validation_label[:, 3]) / 4]

            validation_loss = va_u + va_v + va_p
            # validation_loss_2 = ns_c + ns_u + ns_v + ns_p

            writer.add_scalars('1_loss', {'train': loss,
                                          'validation': validation_loss,
                                          'data_loss': data_loss_1,
                                          'std_loss': data_loss_2,
                                          'icbc_loss': icbc_loss}, iter)
            # writer.add_scalars('2_loss', {'train': loss_2,
            #                               'validation': validation_loss_2,
            #                               'data_loss': data_loss_2}, iter)

            writer.add_scalars('pde_loss', {'loss': pde_loss,
                                            # 'loss_c': les_loss_c,
                                            'loss_u': loss_u,  # + c_loss_u,
                                            'loss_v': loss_v,  # + c_loss_v,
                                            'loss_div': loss_div,  # + c_loss_div
                                            }, iter)
            # writer.add_scalars('pde_loss', {'loss': pde_loss,
            #                                 'loss_c': pde_loss_c,
            #                                 'loss_u': pde_loss_u,
            #                                 'loss_v': pde_loss_v,
            #                                 'loss_p': pde_loss_div}, iter)

            writer.add_scalars('validation_loss', {'total': validation_loss,
                                                   'u': va_u, 'v': va_v, 'p': va_p}, iter)
            # writer.add_scalars('ns_validation_loss', {'total': validation_loss_2,
            #                                           'c': ns_c, 'u': ns_u,
            #                                           'v': ns_v, 'p': ns_p}, iter)

            test_out = NN(t_x_y_grid).cpu().detach().numpy()
            img = fig2data(x_grid, y_grid, test_out[:, 0], test_out[:, 1], test_out[:, 2])
            writer.add_image('%d' % iter, img, dataformats='HWC')

            loss.backward()  #
            opt.step()
            # loss_2.backward()
            # opt_ns.step()

            if store and iter % 50 == 0:
                state = {'model': NN.state_dict(),
                         'optimizer': opt.state_dict(),
                         'epoch': epoch}
                torch.save(state, module_name + '_rec')

            if validation_loss.item() < min_loss:
                min_loss = validation_loss.item()
                print('______Best loss model %.8f______' % loss.item())
                print('NS loss is %.8f' % pde_loss.item())
                print('DATA loss is %.8f' % data_loss_1.item())
                print('Validation loss is %.8f' % validation_loss.item())
                # print('***** Lr = %.8f *****' % opt.state_dict()['param_groups'][0]['lr'])
                if store:
                    state = {'model': NN.state_dict(),
                             'optimizer': opt.state_dict(),
                             'epoch': epoch}
                    torch.save(state, module_name)

            if iter > ITERATION:
                break

        print('------%d epoch------' % epoch)
        if iter > ITERATION:
            break
