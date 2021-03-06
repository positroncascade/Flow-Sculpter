
import os.path
import time

import numpy as np
import tensorflow as tf

import sys
sys.path.append('../')
import model.flow_net as flow_net
from inputs.vtk_data import VTK_data
from inputs.heat_boundary_data_queue import Heat_Sink_Boundary_data
from utils.experiment_manager import make_checkpoint_path

import matplotlib.pyplot as plt

FLAGS = tf.app.flags.FLAGS

TRAIN_DIR = make_checkpoint_path(FLAGS.base_dir_boundary_heat, FLAGS, network="boundary")

shape = FLAGS.dims*[FLAGS.obj_size]

def train():
  """Train ring_net for a number of steps."""
  with tf.Graph().as_default():
    # global step counter
    global_step = tf.get_variable('global_step', [], initializer=tf.constant_initializer(0), trainable=False)

    # make inputs
    input_dims = FLAGS.nr_boundary_params
    inputs_vector, true_boundary = flow_net.inputs_boundary(input_dims, FLAGS.batch_size, shape) 
    noise = tf.random_normal(shape=tf.shape(inputs_vector), mean=0.0, stddev=0.000, dtype=tf.float32) 
    inputs_vector_noise = inputs_vector + noise

    # create and unrap network
    predicted_boundary = flow_net.inference_boundary(FLAGS.batch_size, shape, inputs_vector_noise) 

    # calc error
    error = flow_net.loss_boundary(true_boundary, predicted_boundary)

    # train hopefuly 
    train_op = flow_net.train(error, FLAGS.lr, train_type="boundary_network", global_step=global_step)

    # List of all Variables
    variables = tf.global_variables()

    # Build a saver
    saver = tf.train.Saver(tf.global_variables())   

    # Summary op
    summary_op = tf.summary.merge_all()
 
    # Build an initialization operation to run below.
    init = tf.global_variables_initializer()

    # Start running operations on the Graph.
    sess = tf.Session()

    # init if this is the very time training
    sess.run(init)
 
    # init from checkpoint
    variables_to_restore = tf.all_variables()
    variables_to_restore_flow = [variable for i, variable in enumerate(variables_to_restore) if ("boundary_network" in variable.name[:variable.name.index(':')]) or ("global_step" in variable.name[:variable.name.index(':')])]
    saver_restore = tf.train.Saver(variables_to_restore_flow)
    ckpt = tf.train.get_checkpoint_state(TRAIN_DIR)
    if ckpt is not None:
      print("init from " + TRAIN_DIR)
      try:
         saver_restore.restore(sess, ckpt.model_checkpoint_path)
      except:
         tf.gfile.DeleteRecursively(TRAIN_DIR)
         tf.gfile.MakeDirs(TRAIN_DIR)
         print("there was a problem using variables in checkpoint, random init will be used instead")

    # Start que runner
    tf.train.start_queue_runners(sess=sess)

    # Summary op
    graph_def = sess.graph.as_graph_def(add_shapes=True)
    summary_writer = tf.summary.FileWriter(TRAIN_DIR, graph_def=graph_def)

    # make boundary dataset
    dataset = Heat_Sink_Boundary_data("../../data/", size=128, num_params=15)
    dataset.parse_data()

    # calc number of steps left to run
    run_steps = FLAGS.max_steps - int(sess.run(global_step))
    print(sess.run(global_step))
    for step in xrange(run_steps):
      current_step = sess.run(global_step)
      t = time.time()
      batch_params, batch_boundary = dataset.minibatch(batch_size=FLAGS.batch_size, signed_distance_function=FLAGS.sdf)
      _ , loss_value, gen_boundary = sess.run([train_op, error, predicted_boundary],feed_dict={inputs_vector: batch_params, true_boundary: batch_boundary})
      elapsed = time.time() - t

      assert not np.isnan(loss_value), 'Model diverged with loss = NaN'

      if current_step%100 == 0:
        print("loss value at " + str(loss_value))
        print("time per batch is " + str(elapsed))

      if current_step%1000 == 0:
        summary_str = sess.run(summary_op, feed_dict={inputs_vector: batch_params, true_boundary: batch_boundary})
        summary_writer.add_summary(summary_str, current_step) 
        checkpoint_path = os.path.join(TRAIN_DIR, 'model.ckpt')
        saver.save(sess, checkpoint_path, global_step=global_step)  
        print("saved to " + TRAIN_DIR)

def main(argv=None):  # pylint: disable=unused-argument
  train()

if __name__ == '__main__':
  tf.app.run()
