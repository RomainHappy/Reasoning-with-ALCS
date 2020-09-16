"""
    This Source Code Form is subject to the terms of the Mozilla Public
    License, v. 2.0. If a copy of the MPL was not distributed with this
    file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


import random


def update_classifier_q_learning(
        cl, 
        step_reward: int, 
        max_fitness: float,
        beta_rl: float, 
        gamma: float
    ):
    """
    Applies adapted Q-Learning according to current reinforcement
    `reward` and back-propagated reinforcement `maximum_fitness`.

    Classifier parameters are updated.

    Parameters
    ----------
    cl:
        classifier with `r` and `ir` properties
    step_reward: int
        current reward obtained from the environment after executing step
    max_fitness: float
        maximum fitness - back-propagated reinforcement. Maximum fitness
        from the match set
    beta: float
        learning rate
    gamma: float
        reinforcement rate
    """
    _reward = step_reward + gamma * max_fitness
    cl.ra += beta_rl * (_reward - cl.ra)
    cl.rb += beta_rl * (_reward - cl.rb)
    cl.ir += beta_rl * (step_reward - cl.ir)


def update_classifier_double_q_learning(
        cl, 
        step_reward: int, 
        max_fitness_ra: float,
        max_fitness_rb: float,
        gamma: float
    ):
    """
    Applies adapted Double Q-Learning according to current reinforcement
    `reward` and back-propagated reinforcement `maximum_fitness`.

    Classifier parameters are updated.

    Parameters
    ----------
    cl:
        classifier with `r` and `ir` properties
    step_reward: int
        current reward obtained from the environment after executing step
    max_fitness_ra: float
        maximum fitness - back-propagated reinforcement. Maximum fitness
        from the action set and from the Q_a function
    max_fitness_rb: float
        maximum fitness - back-propagated reinforcement. Maximum fitness
        from the action set and from the Q_b function
    gamma: float
        reinforcement rate
    """
    if random.random() < 0.5:
        nb_of_actions = 1
        if cl.behavioral_sequence:
            nb_of_actions += len(cl.behavioral_sequence)
        beta_rl = pow(cl.nta * nb_of_actions, 0.8)
        beta_rl = 1. / beta_rl
        cl.ra += beta_rl * (step_reward + gamma * max_fitness_rb - cl.ra)
        cl.nta += 1.
    else:
        nb_of_actions = 1
        if cl.behavioral_sequence:
            nb_of_actions += len(cl.behavioral_sequence)
        beta_rl = pow(cl.ntb * nb_of_actions, 0.8)
        beta_rl = 1. / beta_rl
        cl.rb += beta_rl * (step_reward + gamma * max_fitness_ra - cl.rb)
        cl.ntb += 1.
    cl.ir += beta_rl * (step_reward - cl.ir)
