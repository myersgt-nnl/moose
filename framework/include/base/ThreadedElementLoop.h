/****************************************************************/
/*               DO NOT MODIFY THIS HEADER                      */
/* MOOSE - Multiphysics Object Oriented Simulation Environment  */
/*                                                              */
/*           (c) 2010 Battelle Energy Alliance, LLC             */
/*                   ALL RIGHTS RESERVED                        */
/*                                                              */
/*          Prepared by Battelle Energy Alliance, LLC           */
/*            Under Contract No. DE-AC07-05ID14517              */
/*            With the U. S. Department of Energy               */
/*                                                              */
/*            See COPYRIGHT for full restrictions               */
/****************************************************************/

#ifndef THREADEDELEMENTLOOP_H
#define THREADEDELEMENTLOOP_H

#include "ParallelUniqueId.h"
#include "FEProblem.h"
#include "ThreadedElementLoopBase.h"

// Forward declarations
class SystemBase;

/**
 * This mutex is used by all derived classes of the ThreadedElementLoop. It
 * is necessary to protect the creation of the strings used in the propogation
 * of the error messages.  It's possible for a thread to have acquired the
 * commonly used mutex in the Threads namespace so this one is here to
 * avoid any deadlocking.
 */
static Threads::spin_mutex threaded_element_mutex;

/**
 * Base class for assembly-like calculations.
 */
template<typename RangeType>
class ThreadedElementLoop : public ThreadedElementLoopBase<RangeType>
{
public:
  ThreadedElementLoop(FEProblem & feproblem, SystemBase & system);

  ThreadedElementLoop(ThreadedElementLoop & x, Threads::split split);

  virtual ~ThreadedElementLoop();

  virtual void caughtMooseException(MooseException & e);

  virtual bool keepGoing() { return !_fe_problem.hasException(); }
protected:
  SystemBase & _system;
  FEProblem & _fe_problem;
};


template<typename RangeType>
ThreadedElementLoop<RangeType>::ThreadedElementLoop(FEProblem & fe_problem, SystemBase & system) :
    ThreadedElementLoopBase<RangeType>(system.mesh()),
    _system(system),
    _fe_problem(fe_problem)
{
}

template<typename RangeType>
ThreadedElementLoop<RangeType>::ThreadedElementLoop(ThreadedElementLoop & x, Threads::split /*split*/) :
    ThreadedElementLoopBase<RangeType>(x),
    _system(x._system),
    _fe_problem(x._fe_problem)
{
}

template<typename RangeType>
ThreadedElementLoop<RangeType>::~ThreadedElementLoop()
{
}

template<typename RangeType>
void
ThreadedElementLoop<RangeType>::caughtMooseException(MooseException & e)
{
  Threads::spin_mutex::scoped_lock lock(threaded_element_mutex);

  std::string what(e.what());
  _fe_problem.setException(what);
}


#endif //THREADEDELEMENTLOOP_H
