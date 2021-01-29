import argparse
import datetime
import os
import torch
import torch.backends.cudnn as cudnn
import models
from config import cfg
from data import fetch_dataset, make_data_loader, split_dataset
from metrics import Metric
from assist import Assist
from utils import save, load, process_control, process_dataset, resume
from logger import Logger

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
cudnn.benchmark = True
parser = argparse.ArgumentParser(description='cfg')
for k in cfg:
    exec('parser.add_argument(\'--{0}\', default=cfg[\'{0}\'], type=type(cfg[\'{0}\']))'.format(k))
parser.add_argument('--control_name', default=None, type=str)
args = vars(parser.parse_args())
for k in cfg:
    cfg[k] = args[k]
if args['control_name']:
    cfg['control'] = {k: v for k, v in zip(cfg['control'].keys(), args['control_name'].split('_'))} \
        if args['control_name'] != 'None' else {}
cfg['control_name'] = '_'.join(
    [cfg['control'][k] for k in cfg['control'] if cfg['control'][k]]) if 'control' in cfg else ''


def main():
    process_control()
    seeds = list(range(cfg['init_seed'], cfg['init_seed'] + cfg['num_experiments']))
    for i in range(cfg['num_experiments']):
        model_tag_list = [str(seeds[i]), cfg['data_name'], cfg['model_name'], cfg['control_name']]
        cfg['model_tag'] = '_'.join([x for x in model_tag_list if x])
        print('Experiment: {}'.format(cfg['model_tag']))
        runExperiment()
    return


def runExperiment():
    seed = int(cfg['model_tag'].split('_')[0])
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    dataset = fetch_dataset(cfg['data_name'])
    process_dataset(dataset)
    dataset = {'test': dataset['test']}
    last_epoch, assist, organization, _ = resume(cfg['model_tag'], load_tag='checkpoint')
    assist.reset()
    metric = Metric({'test': ['Loss']})
    current_time = datetime.datetime.now().strftime('%b%d_%H-%M-%S')
    logger_path = 'output/runs/test_{}_{}'.format(cfg['model_tag'], current_time)
    test_logger = Logger(logger_path)
    initialize(dataset, assist, organization[0], metric, test_logger, 0)
    for epoch in range(1, last_epoch):
        test_logger.safe(True)
        data_loader = assist.broadcast(dataset, epoch)
        organization_outputs = gather(data_loader, organization, epoch)
        assist.update(organization_outputs, epoch)
        test(assist, metric, test_logger, epoch)
        test_logger.safe(False)
        test_logger.reset()
    test_logger.safe(False)
    assist.reset()
    _, _, _, train_logger = resume(cfg['model_tag'], load_tag='checkpoint')
    save_result = {'cfg': cfg, 'epoch': last_epoch, 'assist': assist,
                   'logger': {'train': train_logger, 'test': test_logger}}
    save(save_result, './output/result/{}.pt'.format(cfg['model_tag']))
    return


def initialize(dataset, assist, organization, metric, logger, epoch):
    logger.safe(True)
    data_loader = make_data_loader(dataset, assist.model_name[0][epoch])
    organization.test(epoch, data_loader['test'], metric, logger)
    info = {'info': ['Model: {}'.format(cfg['model_tag']), 'Test Epoch: {}({:.0f}%)'.format(epoch, 100.)]}
    logger.append(info, 'test', mean=False)
    print(logger.write('test', metric.metric_name['test']))
    logger.safe(False)
    logger.reset()
    for split in dataset:
        assist.organization_output[0][split] = organization.predict(epoch, data_loader[split])['target']
        assist.organization_target[0][split] = torch.tensor(dataset[split].target)
    return


def gather(data_loader, organization, epoch):
    with torch.no_grad():
        num_organizations = len(organization)
        organization_outputs = [{split: None for split in data_loader[i]} for i in range(num_organizations)]
        for i in range(num_organizations):
            for split in organization_outputs[i]:
                organization_outputs[i][split] = organization[i].predict(epoch, data_loader[i][split])['target']
    return organization_outputs


def test(assist, metric, logger, epoch):
    with torch.no_grad():
        input_size = assist.organization_target[0]['test'].size(0)
        input = {'target': assist.organization_target[0]['test']}
        output = {'target': assist.organization_output[epoch]['test']}
        output['loss'] = models.loss_fn(output['target'], input['target'])
        evaluation = metric.evaluate(metric.metric_name['test'], input, output)
        logger.append(evaluation, 'test', n=input_size)
        info = {'info': ['Model: {}'.format(cfg['model_tag']), 'Test Epoch: {}({:.0f}%)'.format(epoch, 100.)]}
        logger.append(info, 'test', mean=False)
        print(logger.write('test', metric.metric_name['test']))
    return


def resume(model_tag, load_tag='checkpoint', verbose=True):
    if os.path.exists('./output/model/{}_{}.pt'.format(model_tag, load_tag)):
        checkpoint = load('./output/model/{}_{}.pt'.format(model_tag, load_tag))
        last_epoch = checkpoint['epoch']
        assist = checkpoint['assist']
        organization = checkpoint['organization']
        logger = checkpoint['logger']
        if verbose:
            print('Resume from {}'.format(last_epoch))
    else:
        print('Not exists model tag: {}, start from scratch'.format(model_tag))
        from datetime import datetime
        from logger import Logger
        last_epoch = 1
        feature_split = split_dataset(cfg['num_users'])
        assist = Assist(feature_split)
        organization = None
        logger_path = 'output/runs/train_{}_{}'.format(cfg['model_tag'], datetime.now().strftime('%b%d_%H-%M-%S'))
        logger = Logger(logger_path)
    return last_epoch, assist, organization, logger


if __name__ == "__main__":
    main()
