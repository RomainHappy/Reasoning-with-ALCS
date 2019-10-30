from random import random
from typing import Optional

from bacs import Perception
from bacs.agents.bacs import Classifier, ClassifiersList, Condition, Configuration, PMark


def cover(p0: Perception,
          action: int,
          p1: Perception,
          time: int,
          cfg: Configuration) -> Classifier:
    """
    Covering - creates a classifier that anticipates a change correctly.
    The reward of the new classifier is set to 0 to prevent *reward bubbles*
    in the environmental model.

    Parameters
    ----------
    p0: Perception
        previous perception
    action: int
        chosen action
    p1: Perception
        current perception
    time: int
        current epoch
    cfg: Configuration
        algorithm configuration class

    Returns
    -------
    Classifier
        new classifier
    """
    # In paper it's advised to set experience and reward of newly generated
    # classifier to 0. However in original code these values are initialized
    # with defaults 1 and 0.5 correspondingly.
    new_cl = Classifier(action=action, experience=1, reward=0.5, cfg=cfg)
    new_cl.tga = time
    new_cl.talp = time

    new_cl.specialize(p0, p1)

    return new_cl


def specification_of_unchanging_components_status(condition: Condition,
                  mark: PMark,
                  p0: Perception) -> bool:
    """
    Check if the specification of unchanging components succeed or failed.
    Help to detect aliased states in POMDPs.

    Parameters
    ----------
    :param condition:
    :param mark:
    :param p0:

    Returns
    -------
    :return: bool
    """
    if mark.one_situation_in_mark():
        situation = Condition(condition)
        for idx, item in enumerate(condition):
            if item == condition.wildcard:
                situation[idx] = ''.join(str(s) for s in mark[idx])
        return not situation.does_match(p0)
    return True

def passthrough(percept, A, B, L, wildcard):
    for i in range(L):
        if B[i] == wildcard:
            percept[i] = A[i]
        else:
            percept[i] = B[i]

def create_behavioral_classifier(
        last_activated_classifier: Classifier,
        cl: Classifier) -> Optional[Classifier]:
    if last_activated_classifier and last_activated_classifier.does_anticipate_change() and cl.does_anticipate_change():
        child = Classifier(
            action=last_activated_classifier.action, 
            behavioral_sequence=[],
            cfg=cl.cfg,
            intermediate_perceptions=[],
            quality=max(last_activated_classifier.q, 0.5))
        if last_activated_classifier.behavioral_sequence:
            child.behavioral_sequence.extend(last_activated_classifier.behavioral_sequence)
        if last_activated_classifier.intermediate_perceptions:
            child.intermediate_perceptions.extend(last_activated_classifier.intermediate_perceptions)
        child.behavioral_sequence.append(cl.action)
        if cl.behavioral_sequence:
            child.behavioral_sequence.extend(cl.behavioral_sequence)
        if cl.intermediate_perceptions:
            child.intermediate_perceptions.extend(cl.intermediate_perceptions)
        if len(child.behavioral_sequence) <= child.cfg.bs_max:
            # Passthrough operation on child condition - An alternative should be to use directly the condition of the last activated classifier
            passthrough(child.condition, cl.condition, last_activated_classifier.condition, cl.cfg.classifier_length,cl.cfg.classifier_wildcard)
            # Passthrough operation on child effect
            passthrough(child.effect, last_activated_classifier.effect, cl.effect, cl.cfg.classifier_length,cl.cfg.classifier_wildcard)
            for idx, effect_item in enumerate(child.effect):
                if effect_item != cl.cfg.classifier_wildcard and effect_item == child.condition[idx]:
                    child.effect[idx] = cl.cfg.classifier_wildcard
            if child.does_anticipate_change():
                return child
    return None

def expected_case(last_activated_classifier: Classifier,
                  cl: Classifier,
                  p0: Perception,
                  time: int) -> Optional[Classifier]:
    """
    Controls the expected case of a classifier. If the classifier
    is too specific it tries to add some randomness to it by
    generalizing some attributes.
    Controls also the case when the specification of unchanging
    components failed by creating classifiers with action chunks.

    :param last_activated_classifier:
    :param cl:
    :param p0:
    :param time:
    :return: new classifier or None
    """

    if not specification_of_unchanging_components_status(cl.condition, cl.mark, p0):
        child = create_behavioral_classifier(last_activated_classifier, cl)
        if child:
            child.intermediate_perceptions.append(p0)
            return child

    diff = cl.mark.get_differences(p0)
    if diff.specificity == 0:
        cl.increase_quality()
        return None

    no_spec = len(cl.specified_unchanging_attributes)
    no_spec_new = diff.specificity
    child = cl.copy_from(cl, time)

    if no_spec >= cl.cfg.u_max:
        while no_spec >= cl.cfg.u_max:
            res = cl.generalize_unchanging_condition_attribute()
            assert res is True
            no_spec -= 1

        while no_spec + no_spec_new > cl.cfg.u_max:
            if random() < 0.5:
                diff.generalize_specific_attribute_randomly()
                no_spec_new -= 1
            else:
                if cl.generalize_unchanging_condition_attribute():
                    no_spec -= 1
    else:
        while no_spec + no_spec_new > cl.cfg.u_max:
            diff.generalize_specific_attribute_randomly()
            no_spec_new -= 1

    child.condition.specialize_with_condition(diff)

    if child.q < 0.5:
        child.q = 0.5

    return child


def expected_case_bs(cl: Classifier,
                  p0: Perception,
                  time: int) -> Optional[Classifier]:
    """
    Controls the expected case of a behavioral classifier.

    :param cl:
    :param p0:
    :param time:
    :return: new classifier or None
    """

    diff = cl.mark.get_differences(p0)
    if diff.specificity == 0:
        cl.increase_quality()
        return None

    child = cl.copy_from(cl, time)
    child.condition.specialize_with_condition(diff)

    if child.q < 0.5:
        child.q = 0.5

    return child


def unexpected_case(cl: Classifier,
                    p0: Perception,
                    p1: Perception,
                    time: int) -> Optional[Classifier]:
    """
    Controls the unexpected case of the classifier.

    :param cl:
    :param p0:
    :param p1:
    :param time:
    :return: specialized classifier if generation was possible,
    None otherwise
    """
    cl.decrease_quality()
    cl.set_mark(p0)

    # Return if the effect is not specializable
    if not cl.effect.is_specializable(p0, p1):
        return None

    child = cl.copy_from(cl, time)

    child.specialize(p0, p1, leave_specialized=True)

    if child.q < 0.5:
        child.q = 0.5

    return child
