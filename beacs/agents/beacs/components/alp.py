"""
    This Source Code Form is subject to the terms of the Mozilla Public
    License, v. 2.0. If a copy of the MPL was not distributed with this
    file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from random import random
from typing import Optional

from beacs import Perception
from beacs.agents.beacs import Classifier, ClassifiersList, Condition, Configuration, PMark
from beacs.agents.beacs.components.aliasing_detection import is_state_aliased


def cover(
        p0: Perception,
        action: int,
        p1: Perception,
        time: int,
        cfg: Configuration
    ) -> Classifier:
    """
    Covering - creates a classifier that anticipates a change correctly.

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
    new_cl = Classifier(
        action=action, 
        tga=time,
        tbseq=time,
        talp=time,
        cfg=cfg
    )
    new_cl.specialize(p0, p1)
    return new_cl


def expected_case(
        cl: Classifier,
        p0: Perception,
        p1: Perception,
        time: int,
        cfg: Configuration,
    ):
    """
    Controls the expected case of a classifier with the help of 
    Specification of Unchanging Components.

    Returns
    ----------
    Bool related to aliasing, New classifier or None
    """
    is_aliasing_detected = False

    if cl.is_enhanced() and cl.aliased_state == p0:
        is_aliasing_detected = True

    if is_state_aliased(cl.condition, cl.mark, p0):
        if cl.cfg.do_pep: cl.ee = True
        is_aliasing_detected = True

    diff = cl.mark.get_differences(p0)
    if diff.specificity == 0:
        cl.increase_quality()
        return is_aliasing_detected, None

    child = cl.copy_from(cl, time)

    spec = cl.specificity
    spec_new = diff.specificity
    if spec >= child.cfg.u_max:
        while spec >= child.cfg.u_max:
            child.generalize_specific_attribute_randomly()
            spec -= 1
        while spec + spec_new > child.cfg.u_max:
            if spec > 0 and random() < 0.5:
                child.generalize_specific_attribute_randomly()
                spec -= 1
            else:
                diff.generalize_specific_attribute_randomly()
                spec_new -= 1
    else:
        while spec + spec_new > child.cfg.u_max:
            diff.generalize_specific_attribute_randomly()
            spec_new -= 1

    child.condition.specialize_with_condition(diff)

    child.q = max(0.5, child.q)

    return is_aliasing_detected, child


def unexpected_case(
        cl: Classifier,
        p0: Perception,
        p1: Perception,
        time: int
    ) -> Optional[Classifier]:
    """
    Controls the unexpected case of the classifier.

    Returns
    ----------
    Specialized classifier if generation was possible, otherwise None
    """
    cl.decrease_quality()
    cl.set_mark(p0)
    # If nothing can be done, stop specialization of the classifier
    if not cl.effect.is_specializable(p0, p1, cl.aliased_state):
        return None
    # If the classifier is not enhanced, directly specialize it
    if not cl.is_enhanced():
        child = cl.copy_from(cl, time)
        child.specialize(p0, p1)
        child.q = max(0.5, child.q)
        return child
    # Otherwise the classifier is enhanced and p0 corresponds to the aliased state of cl
    # If the classifier is enhanced, try to append a new effect if it is no included in the list of effects
    child = cover(p0, cl.action, p1, time, cl.cfg)
    child.q = max(0.5, cl.q)
    child.ra = cl.ra
    child.rb = cl.rb
    if not cl.effect.subsumes(child.effect):
        return cl.merge_with(child, p0, time)
    # Otherwise, try to only specialize condition and indicate items that cannot be generalized
    child.condition.specialize_with_condition(cl.condition)
    for index in range(child.cfg.classifier_length):
        child.effect.enhanced_trace_ga[index] = cl.effect.enhanced_trace_ga[index]
        if cl.condition[index] == cl.condition.wildcard and child.condition[index] != child.condition.wildcard:
            cl.effect.enhanced_trace_ga[index] = False
            child.effect.enhanced_trace_ga[index] = False
    return child