''' Thin Cosine Similarity MLP

    With N training samples, generate a new dataset
    where the i-th training sample is (w_i(1), w_i(2), w_i(3)).

    The input to the MLP is 600 node layer with 200 node
    layer (lemma vector). Not all connections persist. Character
    level connections.

    o_{i}(j) ~ (w_{i}^{1}(j)m w_{i}^{2}(j)m w_{i}^{3}(j))

    The MLP uses identity function (no bounded nonlinearities).
    Cost function uses cosine similiarity between real lemma and
    predicted word.

    Use an LSH to convert vector back to word.
'''

from __future__ import absolute_import
from __future__ import print_function

import autograd.numpy as np
import autograd.scipy.stats.norm as norm
from autograd import grad


def cosine_dist(v1, v2):
    prod = np.dot(v1, v2.T)
    len1 = np.sqrt(np.dot(v1, v1.T))
    len2 = np.sqrt(np.dot(v2, v2.T))
    return prod / (len1 * len2)

def identity(X): return X

def build(input_count,
          output_count,
          nonlinearity=identity):
    ''' Builds the multi-layer perceptron. Assume that any/all
        one-hot encoding has already been done. This supports
        continuous regression only.
        Args
        ----
        input_count : integer
                      number of features in observations
        output_count : integer
                       number of features in outputs
        state_counts : list
                       list of internal hidden units. Each index represents
                       a new hidden layer.
        Returns
        -------
        prediction: lambda function
                    inputs are (weights, observation)
        log_likelihood: lambda function
                        inputs are (weights, observation, outputs)
        num_weights: integer
                     number of weights in general
    '''

    # only connections from the same letters exist
    layer_sizes = [input_count, output_count]
    num_reps = input_count / output_count
    num_weights = (num_reps+1) * output_count  # bias
    base_idx = np.array([i for i in range(num_weights) if i % output_count == 0])

    def outputs(weights, inputs):
        outputs = np.zeros((inputs.shape[0], output_count))
        for i in range(output_count):
            mask = weights[base_idx+i]
            W, b = mask[:-1], mask[-1]
            I = inputs[:, base_idx[:-1]+i]
            outputs[:, i] = np.dot(I, W) + b
        outputs = nonlinearity(outputs)
        return outputs

    def log_likelihood(weights, inputs, outputs):
        ''' Measure likelihoods by 1 - cosine similiarity between
            the predicted and the real lemma vectors '''
        preds = outputs(weights, inputs)
        dists = 0
        for i in range(inputs.shape[0]):
            dists += (1 - cosine_dist(preds[i, :], outputs[i, :]))
        log_lik = np.log(dists / inputs.shape[0])
        return log_lik

    return outputs, log_likelihood, num_weights


def train_mlp(
        obs_set,
        out_set,
        init_weights=None,
        num_epochs=100,
        batch_size=128,
        param_scale=0.01):

    input_count = obs_set.shape[0]
    output_count = out_set.shape[0]
    num_batches = int(np.ceil(obs_set.shape[1] / float(batch_size)))

    pred_fun, loglike_fun, num_weights = mlp.build(
        input_count, output_count)

    if init_weights is None:
        init_weights = np.random.randn(num_weights) * param_scale

    def batch_indices(iter):
        idx = iter % num_batches
        return slice(idx * batch_size, (idx+1) * batch_size)

    def loss(weights, x, y):
        return -loglike_fun(weights, x, y)

    def batch_loss(weights, iter):
        idx = batch_indices(iter)
        return loss(weights, obs_set[:, idx], out_set[:, idx])

    def callback(x, i, g):
        print('iter {}  |  training loss {}'.format(
            i, loss(x, obs_set, out_set)))

    grad_fun = grad(batch_loss)
    trained_weights = adam(grad_fun,
                           init_weights,
                           callback=callback,
                           num_iters=num_epochs)

    return pred_fun, loglike_fun, trained_weights

