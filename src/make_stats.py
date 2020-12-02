import os
from config import cfg
from data import fetch_dataset, make_data_loader
from utils import save, collate, Stats, makedir_exist_ok, process_control

if __name__ == "__main__":
    stats_path = './res/stats'
    subset = 'label'
    dim = 1
    data_names = ['Blob', 'Iris', 'Diabetes', 'BostonHousing', 'Wine', 'BreastCancer', 'QSAR', 'MNIST', 'CIFAR10']
    process_control()
    cfg['tag'] = {'batch_size': {'train': 128, 'test': 128}}
    for data_name in data_names:
        dataset = fetch_dataset(data_name, subset)
        data_loader = make_data_loader(dataset, cfg['model_name'])
        stats = Stats(dim=dim)
        for i, input in enumerate(data_loader['train']):
            input = collate(input)
            stats.update(input['data'])
        stats = (stats.mean.tolist(), stats.std.tolist())
        print(data_name, stats)
        makedir_exist_ok(stats_path)
        save(stats, os.path.join(stats_path, '{}.pt'.format(data_name)))