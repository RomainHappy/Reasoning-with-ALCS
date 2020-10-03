"""
    This Source Code Form is subject to the terms of the Mozilla Public
    License, v. 2.0. If a copy of the MPL was not distributed with this
    file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import random
from itertools import groupby

from epeacs.agents.epeacs import Classifier


def choose_classifier(cll, cfg, epsilon: float) -> Classifier:
    """
    Chooses which classifier to use given matching set

    Parameters
    ----------
    cll: ClassifierList
        Matching set
    cfg: Configuration
        Allow to retrieve the number of possible actions
    epsilon: float
        Probability of executing exploration path

    Returns
    -------
    Classifier
    """
    if random.random() < epsilon:
        return explore(cll, cfg)

    return choose_fittest_classifier(cll, cfg)


def explore(cll, cfg, pb: float = 0.5) -> Classifier:
    """
    Chooses classifier according to current exploration policy

    Parameters
    ----------
    cll: ClassifierList
        Matching set
    cfg: Configuration
        Allow to retrieve the number of possible actions
    pb: float
        probability of biased exploration

    Returns
    -------
    Classifier
        Chosen classifier
    """
    rand = random.random()
    if rand < pb:
        return choose_random_classifiers(cll, cfg)
    elif rand < pb + 2*(1. - pb)/5.: #pb+ (1. - pb)/3. with 3 being the number of biases
        return choose_action_from_knowledge_array(cll, cfg)
    elif rand < pb + 4*(1. - pb)/5.: #pb+ 2*(1. - pb)/3. with 3 being the number of biases
        return choose_latest_action(cll, cfg)
    else:
        return choose_behavioral_sequence(cll, cfg)


def choose_behavioral_sequence(cll, cfg) -> Classifier:
    if len(cll) > 0:
        behavioral_classifiers = [cl for cl in cll if cl.behavioral_sequence]
        if len(behavioral_classifiers) > 0:
            experience_array = {}
            experience_array_num = {}
            for bcl in behavioral_classifiers:
                sequence = [bcl.action]
                sequence.extend(bcl.behavioral_sequence)
                sequence = tuple(sequence)
                if sequence not in experience_array:
                    experience_array[sequence] = bcl.exp * bcl.num
                    experience_array_num[sequence] = bcl.num
                else:
                    experience_array[sequence] += bcl.exp * bcl.num
                    experience_array_num[sequence] += bcl.num
            less_experienced = -1
            less_experienced_sequence = None
            for sequence in experience_array:
                tmp_exp = experience_array[sequence] / float(experience_array_num[sequence])
                if less_experienced == -1 or less_experienced >= tmp_exp:
                    less_experienced = tmp_exp
                    less_experienced_sequence = list(sequence)
            return Classifier(action=less_experienced_sequence[0], behavioral_sequence=less_experienced_sequence[1:], cfg=cfg)
    return choose_random_classifiers(cll, cfg)


def choose_latest_action(cll, cfg) -> Classifier:
    """
    Computes latest executed action ("action delay bias") and return 
    a corresponding classifier

    Parameters
    ----------
    cll: ClassifierList
        Matching set
    cfg: Configuration
        Allow to retrieve the number of possible actions

    Returns
    -------
    Classifier
    """
    last_executed_cls = None
    number_of_cls_per_action = {i: 0 for i in range(cfg.number_of_possible_actions)}
    if len(cll) > 0:
        last_executed_cls = min(cll, key=lambda cl: cl.talp)
        # If there are some actions with no classifiers - select them
        cll.sort(key=lambda cl: cl.action)
        for _action, _clss in groupby(cll, lambda cl: cl.action):
            number_of_cls_per_action[_action] = sum([cl.num for cl in _clss])
        for action, nCls in number_of_cls_per_action.items():
            if nCls == 0:
                return Classifier(action=action, cfg=cfg)
        return last_executed_cls
    return choose_random_classifiers(cll, cfg)


def choose_action_from_knowledge_array(cll, cfg) -> Classifier:
    """
    Creates 'knowledge array' that represents the average quality of the
    anticipation for each action in the current list. Chosen is
    the action, the system knows least about the consequences.
    Then a classifier that corresponds to this action is randomly returned.

    Parameters
    ----------
    cll: ClassifierList
        Matching set
    cfg: Configuration
        Allow to retrieve the number of possible actions

    Returns
    -------
    Classifier
    """
    knowledge_array = {i: 0.0 for i in range(cfg.number_of_possible_actions)}

    if len(cll) > 0:
        cll.sort(key=lambda cl: cl.action)

        for _action, _clss in groupby(cll, lambda cl: cl.action):
            _classifiers = [cl for cl in _clss]
            agg_q = sum(cl.q * cl.num for cl in _classifiers)
            agg_num = sum(cl.num for cl in _classifiers)
            knowledge_array[_action] = agg_q / float(agg_num)
        by_quality = sorted(knowledge_array.items(), key=lambda el: el[1])
        action = by_quality[0][0]

        classifiers_that_match_action = [cl for cl in cll if cl.action == action]
        if len(classifiers_that_match_action) > 0:
            idx = random.randint(0, len(classifiers_that_match_action) -1)
            return classifiers_that_match_action[idx]

    return choose_random_classifiers(cll, cfg)


def choose_random_classifiers(cll, cfg) -> Classifier:
    """
    Chooses one of the possible actions in the environment randomly 
    and return a corresponding classifier

    Parameters
    ----------
    cll: ClassifierList
        Matching set
    cfg: Configuration
        Allow to retrieve the number of possible actions

    Returns
    -------
    Classifier
    """
    nb_of_cll = len(cll)
    rand = random.randint(0, nb_of_cll + cfg.number_of_possible_actions - 1)
    if rand < nb_of_cll:
        return cll[rand]
    action = rand - nb_of_cll
    return Classifier(action=action, cfg=cfg)


def choose_fittest_classifier(cll, cfg) -> Classifier:
    """
    Chooses the fittest classifier in the matching set

    Parameters
    ----------
    cll: ClassifierList
        Matching set
    cfg: Configuration
        Allow to retrieve the number of possible actions

    Returns
    -------
    Classifier
    """
    if len(cll) > 0:
        # Based on hypothesis that a change should be anticipted
        anticipated_change = [cl for cl in cll if cl.does_anticipate_change()]
        if len(anticipated_change) > 0:
            return max(anticipated_change, key=lambda cl: cl.fitness)
        #return max(cll, key=lambda cl: cl.fitness)
    return choose_random_classifiers(cll, cfg)

