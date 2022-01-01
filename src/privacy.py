import sys
import numpy as np
import matplotlib.pyplot as plt


def dp(y, alpha=1):
    '''
    To perturb a continuous-valued numpy vector with additive Laplace noise, evaluated by DP,
    where the noise level is connected with the privacy leakage parameter alpha
    Input
        y: numpy vector
        alpha: a float value in (0, infty). smaller means more private, more noisy

    Output
        y_dp: numpy vector of the same shape as y
    '''
    # truncate y into the bounded range of [a, b], where T is determined by 2.5% quantile
    a, b = np.quantile(y, 0.025), np.quantile(y, 0.975)
    y_dp = np.copy(y)
    y_dp[y < a] = a
    y_dp[y > b] = b
    y_dp += np.random.laplace(scale=(b - a) / alpha, size=y.shape)
    return y_dp


def ip(y, thresh=1):
    '''
    To perturb a continuous-valued numpy vector with interval noise, evaluated by IP,
    where the privacy leakage parameter is the average interval width

    Input
        y: numpy vector
        thresh: average interval width

    Output
        y_ip: numpy vector of the same shape as y
    '''
    # truncate y into the bounded range of [a, b], where T is determined by 2.5% quantile
    a, b = np.quantile(y, 0.025), np.quantile(y, 0.975)
    t = np.random.uniform(low=a, high=b, size=y.shape)
    y_ip = np.zeros(y.shape, dtype=y.dtype)
    interval = np.zeros((*y.shape, 2))
    interval[..., 0], interval[..., 1] = a, b
    mask_1 = y < t
    mask_2 = y >= t
    interval[mask_1, 1] = np.minimum(t[mask_1], interval[mask_1, 1])
    y_ip[mask_1] += (2 * t[mask_1] - b) / thresh
    interval[mask_2, 0] = np.maximum(t[mask_2], interval[mask_2, 0])
    y_ip[mask_2] += (2 * t[mask_2] - a) / thresh
    y_ = y.reshape(-1, 1)
    interval_ = interval.reshape(1, -1, 2)
    leak = np.logical_and(y_ >= interval_[..., 0], y_ < interval_[..., 1]).mean()
    return y_ip, interval, leak


def make_privacy(input, mode, param):
    if mode == 'dp':
        output = dp(input, param)
    elif mode == 'ip':
        output, _, _ = ip(input, param)
    else:
        raise ValueError('Not valid output')
    return output


if __name__ == '__main__':
    y = np.random.normal(size=100)

    plt.figure(1)
    plt.title('Y versus Y (DP)')
    y_dp = dp(y, alpha=1)
    plt.plot(y, y_dp, '.')
    plt.show()

    plt.figure(2, figsize=(8, 4))
    y_ip, interval, leak = ip(y, thresh=1)
    print('IP privacy leakage (or average interval width) is {}'.format(leak))
    plt.subplot(2, 1, 1)
    plt.title('Y and Y (IP)')
    plt.plot(y, y_ip, '.')
    plt.subplot(2, 1, 2)
    plt.title('Y and IP intervals')
    plt.plot(y, '-')
    plt.plot(interval[:, 0], 'bx-')
    plt.plot(interval[:, 1], 'bx-')
    plt.tight_layout()
    plt.show()

    y = np.random.normal(size=(10, 3, 4, 4))
    print(y.shape)
    y_dp = dp(y, alpha=1)
    y_ip, interval, leak = ip(y, thresh=1)
    print(y_dp.shape, y_ip.shape)
    print('IP privacy leakage (or average interval width) is {}'.format(leak))
