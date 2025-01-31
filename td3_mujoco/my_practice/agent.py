# coding: utf-8
import numpy as np
import parl
from parl import layers
from paddle import fluid
import os

class QuadrotorAgent(parl.Agent):
    def __init__(self, algorithm, obs_dim, act_dim):
        assert isinstance(obs_dim, int)
        assert isinstance(act_dim, int)
        self.obs_dim = obs_dim
        self.act_dim = act_dim
        super(QuadrotorAgent, self).__init__(algorithm)

        # 注意，在最开始的时候，先完全同步target_model和model的参数
        self.alg.sync_target(decay=0)
        
        #CHANGE
        self.learn_it = 0
        self.policy_freq = self.alg.policy_freq

    def build_program(self):
        self.pred_program = fluid.Program()
        # self.learn_program = fluid.Program()
        
        #CHANGE
        self.actor_learn_program = fluid.Program()
        self.critic_learn_program = fluid.Program()

        with fluid.program_guard(self.pred_program):
            obs = layers.data(
                name='obs', shape=[self.obs_dim], dtype='float32')
            self.pred_act = self.alg.predict(obs)

        # with fluid.program_guard(self.learn_program):
        #     obs = layers.data(
        #         name='obs', shape=[self.obs_dim], dtype='float32')
        #     act = layers.data(
        #         name='act', shape=[self.act_dim], dtype='float32')
        #     reward = layers.data(name='reward', shape=[], dtype='float32')
        #     next_obs = layers.data(
        #         name='next_obs', shape=[self.obs_dim], dtype='float32')
        #     terminal = layers.data(name='terminal', shape=[], dtype='bool')
        #     _, self.critic_cost = self.alg.learn(obs, act, reward, next_obs,
        #                                          terminal)
        
        #CHANGE
        with fluid.program_guard(self.actor_learn_program):
            obs = layers.data(
                name='obs', shape=[self.obs_dim], dtype='float32')
            self.actor_cost = self.alg.actor_learn(obs)

        with fluid.program_guard(self.critic_learn_program):
            obs = layers.data(
                name='obs', shape=[self.obs_dim], dtype='float32')
            act = layers.data(
                name='act', shape=[self.act_dim], dtype='float32')
            reward = layers.data(name='reward', shape=[], dtype='float32')
            next_obs = layers.data(
                name='next_obs', shape=[self.obs_dim], dtype='float32')
            terminal = layers.data(name='terminal', shape=[], dtype='bool')
            self.critic_cost = self.alg.critic_learn(obs, act, reward,
                                                     next_obs, terminal)


    def predict(self, obs):
        obs = np.expand_dims(obs, axis=0)
        act = self.fluid_executor.run(
            self.pred_program, feed={'obs': obs},
            fetch_list=[self.pred_act])[0]
        return act

    def learn(self, obs, act, reward, next_obs, terminal):
        feed = {
            'obs': obs,
            'act': act,
            'reward': reward,
            'next_obs': next_obs,
            'terminal': terminal
        }
        critic_cost = self.fluid_executor.run(
            self.critic_learn_program,
            feed=feed,
            fetch_list=[self.critic_cost])[0]
            
        # self.alg.sync_target()
        # return critic_cost  
        
        #CHANGE
        self.learn_it += 1
        actor_cost = None
        if self.learn_it % self.policy_freq == 0:
            actor_cost = self.fluid_executor.run(
                self.actor_learn_program,
                feed={'obs': obs},
                fetch_list=[self.actor_cost])[0]
            self.alg.sync_target()
        return actor_cost, critic_cost
        
    #CHANGE  
    def save_actor(self, save_path):
        program = self.actor_learn_program
        dirname = os.sep.join(save_path.split(os.sep)[:-1])
        filename = save_path.split(os.sep)[-1]
        fluid.io.save_params(
            executor=self.fluid_executor,
            dirname=dirname,
            main_program=program,
            filename=filename)
            
    #CHANGE
    def save_critic(self, save_path):
        program = self.critic_learn_program
        dirname = os.sep.join(save_path.split(os.sep)[:-1])
        filename = save_path.split(os.sep)[-1]
        fluid.io.save_params(
            executor=self.fluid_executor,
            dirname=dirname,
            main_program=program,
            filename=filename)
            
    #CHANGE
    def restore_actor(self, save_path):
        program = self.actor_learn_program
        if type(program) is fluid.compiler.CompiledProgram:
            program = program._init_program
        dirname = os.sep.join(save_path.split(os.sep)[:-1])
        filename = save_path.split(os.sep)[-1]
        fluid.io.load_params(
            executor=self.fluid_executor,
            dirname=dirname,
            main_program=program,
            filename=filename)
    
    #CHANGE
    def restore_critic(self, save_path):
        program = self.critic_learn_program
        if type(program) is fluid.compiler.CompiledProgram:
            program = program._init_program
        dirname = os.sep.join(save_path.split(os.sep)[:-1])
        filename = save_path.split(os.sep)[-1]
        fluid.io.load_params(
            executor=self.fluid_executor,
            dirname=dirname,
            main_program=program,
            filename=filename)



