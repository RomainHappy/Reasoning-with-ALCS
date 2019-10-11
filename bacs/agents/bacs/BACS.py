import logging
from typing import List, Tuple

from bacs import Perception
from bacs.agents.Agent import Agent, TrialMetrics
from bacs.agents.bacs import Classifier, ClassifiersList, Configuration
from bacs.agents.bacs.Condition import Condition
from bacs.agents.bacs.Effect import Effect
from bacs.agents.bacs.components.action_planning_bacs import \
    search_goal_sequence, suitable_cl_exists
from bacs.agents.bacs.components.subsumption_bacs import does_subsume
from bacs.agents.bacs.components.action_selection_bacs import choose_action, choose_fittest_classifier, choose_random_action

import numpy as np

logger = logging.getLogger(__name__)


class BACS(Agent):

    def __init__(self,
                 cfg: Configuration,
                 population: ClassifiersList=None) -> None:
        self.cfg = cfg
        self.population = population or ClassifiersList()

    def get_population(self):
        return self.population

    def clean_population(self):
        for cl in self.population:
            for other in self.population:
                if does_subsume(cl, other, self.cfg.theta_exp):
                    self.population.safe_remove(other)
        pop = [cl for cl in self.population if cl.does_anticipate_change()]
        self.population = ClassifiersList(*pop)
        

    def get_cfg(self):
        return self.cfg

    def _run_trial_explore(self, env, time, current_trial=None) \
            -> TrialMetrics:

        logger.debug("** Running trial explore ** ")
        # Initial conditions
        steps = 0
        raw_state = env.reset()
        state = self.cfg.environment_adapter.to_genotype(raw_state)
        action = env.action_space.sample()
        last_reward = 0
        prev_state = Perception.empty()
        action_set = ClassifiersList()
        done = False

        while not done:
            
            if self.cfg.do_action_planning and \
                    self._time_for_action_planning(steps + time):
                # Action Planning for increased model learning
                steps_ap, state, prev_state, action_set, \
                    action, last_reward = \
                    self._run_action_planning(env, steps + time, state,
                                              prev_state, action_set, action,
                                              last_reward)
                steps += steps_ap
            
            # Creation of the matching set
            match_set = self.population.form_match_set(state)

            if steps > 0:
                # Apply learning in the last action set
                ClassifiersList.apply_alp(
                    self.population,
                    match_set,
                    action_set,
                    prev_state,
                    action,
                    state,
                    time + steps,
                    self.cfg.theta_exp,
                    self.cfg)
                ClassifiersList.apply_reinforcement_learning(
                    action_set,
                    last_reward,
                    match_set.get_maximum_fitness(),
                    self.cfg.beta,
                    self.cfg.gamma
                )
                if self.cfg.do_ga:
                    ClassifiersList.apply_ga(
                        time + steps,
                        self.population,
                        match_set,
                        action_set,
                        state,
                        self.cfg.theta_ga,
                        self.cfg.mu,
                        self.cfg.chi,
                        self.cfg.theta_as,
                        self.cfg.do_subsumption,
                        self.cfg.theta_exp)
            
            action_classifier = choose_action(match_set, self.cfg, self.cfg.prob_x)
            if action_classifier:
                action = action_classifier.action
            else:
                action = choose_random_action(self.cfg.number_of_possible_actions)
            
            # Use environment adapter and create action set
            iaction = self.cfg.environment_adapter.to_lcs_action(action)
            logger.debug("\tExecuting action: [%d]", action)
            action_set = match_set.form_action_set(action)
            # Do the action
            prev_state = state
            raw_state, last_reward, done, _ = env.step(iaction)
            state = self.cfg.environment_adapter.to_genotype(raw_state)

            if done:
                # Apply algorithms
                ClassifiersList.apply_alp(
                    self.population,
                    ClassifiersList(),
                    action_set,
                    prev_state,
                    action,
                    state,
                    time + steps,
                    self.cfg.theta_exp,
                    self.cfg)
                ClassifiersList.apply_reinforcement_learning(
                    action_set,
                    last_reward,
                    0,
                    self.cfg.beta,
                    self.cfg.gamma)
            if self.cfg.do_ga:
                ClassifiersList.apply_ga(
                    time + steps,
                    self.population,
                    ClassifiersList(),
                    action_set,
                    state,
                    self.cfg.theta_ga,
                    self.cfg.mu,
                    self.cfg.chi,
                    self.cfg.theta_as,
                    self.cfg.do_subsumption,
                    self.cfg.theta_exp)

            steps += 1
        return TrialMetrics(steps, last_reward)

    def _run_trial_exploit(self, env, time=None, current_trial=None) \
            -> TrialMetrics:

        logger.debug("** Running trial exploit **")
        # Initial conditions
        steps = 0
        raw_state = env.reset()
        state = self.cfg.environment_adapter.to_genotype(raw_state)
        
        last_reward = 0
        action_set = ClassifiersList()
        done = False

        while not done:

            match_set = self.population.form_match_set(state)

            if steps > 0:
                ClassifiersList.apply_reinforcement_learning(
                    action_set,
                    last_reward,
                    match_set.get_maximum_fitness(),
                    self.cfg.beta,
                    self.cfg.gamma)

            action_classifier = choose_fittest_classifier(match_set)
            if action_classifier:
                action = action_classifier.action
            else:
                action = choose_random_action(self.cfg.number_of_possible_actions)

            iaction = self.cfg.environment_adapter.to_env_action(action)
            action_set = match_set.form_action_set(action)

            # Do the action
            prev_state = state
            raw_state, last_reward, done, _ = env.step(iaction)
            state = self.cfg.environment_adapter.to_genotype(raw_state)

            if done:
                # Apply algorithms
                ClassifiersList.apply_reinforcement_learning(
                    action_set, last_reward, 0, self.cfg.beta, self.cfg.gamma)

            steps += 1

        return TrialMetrics(steps, last_reward)

    def _run_action_planning(self,
                             env,
                             time: int,
                             state: Perception,
                             prev_state: Perception,
                             action_set: ClassifiersList,
                             action: int,
                             last_reward: int) -> Tuple[int, Perception,
                                                        Perception,
                                                        ClassifiersList,
                                                        int, int]:
        """
        Executes action planning for model learning speed up.
        Method requests goals from 'goal generator' provided by
        the environment. If goal is provided, BACS searches for
        a goal sequence in the current model (only the reliable classifiers).
        This is done as long as goals are provided and BACS finds a sequence
        and successfully reaches the goal.

        Parameters
        ----------
        env
        time
        state
        prev_state
        action_set
        action
        last_reward

        Returns
        -------
        steps
        state
        prev_state
        action_set
        action
        last_reward

        """
        logging.debug("** Running action planning **")

        if not hasattr(env.env, "get_goal_state"):
            logging.debug("Action planning stopped - "
                          "no function get_goal_state in env")
            return 0, state, prev_state, action_set, action, last_reward

        steps = 0
        done = False

        while not done:
            goal_situation = self.cfg.environment_adapter.to_genotype(
                env.env.get_goal_state())

            if goal_situation is None:
                break

            act_sequence = search_goal_sequence(self.population, state,
                                                goal_situation)

            # Execute the found sequence and learn during executing
            i = 0
            for act in act_sequence:
                if act == -1:
                    break

                match_set = self.population.form_match_set(state)

                if action_set is not None and len(prev_state) != 0:
                    ClassifiersList.apply_alp(
                        self.population,
                        match_set,
                        action_set,
                        prev_state,
                        action,
                        state,
                        time + steps,
                        self.cfg.theta_exp,
                        self.cfg)
                    ClassifiersList.apply_reinforcement_learning(
                        action_set,
                        last_reward,
                        0,
                        self.cfg.beta,
                        self.cfg.gamma)
                    if self.cfg.do_ga:
                        ClassifiersList.apply_ga(
                            time + steps,
                            self.population,
                            match_set,
                            action_set,
                            state,
                            self.cfg.theta_ga,
                            self.cfg.mu,
                            self.cfg.chi,
                            self.cfg.theta_as,
                            self.cfg.do_subsumption,
                            self.cfg.theta_exp)

                action = act
                action_set = ClassifiersList.form_action_set(match_set, action)

                iaction = self.cfg.environment_adapter.to_lcs_action(action)

                raw_state, last_reward, done, _ = env.step(iaction)
                prev_state = state

                state = self.cfg.environment_adapter.to_genotype(raw_state)

                if not suitable_cl_exists(action_set, prev_state,
                                          action, state):

                    # no reliable classifier was able to anticipate
                    # such a change
                    break

                steps += 1
                i += 1

            if i == 0:
                break

        return steps, state, prev_state, action_set, action, last_reward

    def _time_for_action_planning(self, time):
        return time % self.cfg.action_planning_frequency == 0
