from typing import Callable, Iterator, List, Tuple, Union, Optional

import numpy as np
import scipy.optimize
import tensorflow as tf
from scipy.optimize import OptimizeResult
from .optimize import loss_gradients

__all__ = ['ScipyOptimizer']


tfe = tf.contrib.eager


Loss = tf.Tensor
Variables = List[tfe.Variable]
Gradients = List[tf.Tensor]
StepCallback = Callable[[Loss, Variables, Gradients], None]
LossClosure = Callable[..., Tuple[tf.Tensor, Variables]]


class ScipyOptimizer:
    def minimize(self,
                 closure: LossClosure,
                 variables: Variables,
                 step_callback: Optional[StepCallback] = None,
                 **scipy_kwargs) -> OptimizeResult:
        """
        Minimize is a proxy method for `scipy.optimize.minimize` function.
        Args:
            closure: A closure that re-evaluates the model and returns the loss. The closure
                should clear the gradients, compute the loss and gradients.
            scipy_kwargs: Arguments passed to `scipy.optimize.minimize` method.
        Returns:
            The optimization result represented as a scipy ``OptimizeResult`` object.
            See `OptimizeResult` for a attributes description.
        """
        if not callable(closure):
            raise ValueError('Callable object expected.')
        initial_params = self.initial_parameters(variables)
        func = self.eval_func(closure, variables, step_callback)
        return scipy.optimize.minimize(func, initial_params, jac=True, **scipy_kwargs)

    @classmethod
    def initial_parameters(cls, variables):
        return cls.pack_tensors(variables)

    @classmethod
    def eval_func(cls,
                  closure: LossClosure,
                  variables: Variables,
                  step_callback: Optional[StepCallback] = None):
        def _eval(x):
            cls.unpack_tensors(variables, x)
            loss, grads = loss_gradients(closure, variables)
            if callable(step_callback):
                step_callback(loss, variables, grads)
            return loss.numpy(), cls.pack_tensors(grads)
        return _eval

    @staticmethod
    def pack_tensors(tensors: Iterator[tf.Tensor]) -> np.ndarray:
        flats = [tf.reshape(tensor, (-1,)) for tensor in tensors]
        tensors_vector = tf.concat(flats, axis=0)
        return tensors_vector.numpy()

    @staticmethod
    def unpack_tensors(to_tensors: Iterator[tf.Tensor], from_vector: np.ndarray):
        s = 0
        for tensor in to_tensors:
            shape = tensor.shape
            tensor_size = np.prod(shape)
            tensor_vector = from_vector[s: s + tensor_size]
            tensor_vector = tf.reshape(tensor_vector, shape)
            tensor.assign(tensor_vector)
            s += tensor_size
