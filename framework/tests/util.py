import os, re
from subprocess import *
from time import strftime, gmtime, ctime, localtime, asctime

TERM_COLS = 110

## Run a command and return the output, or ERROR: + output if retcode != 0
def runCommand(cmd):
  p = Popen([cmd],stdout=PIPE,stderr=STDOUT, close_fds=True, shell=True)
  output = p.communicate()[0]
  if (p.returncode != 0):
    output = 'ERROR: ' + output
  return output

## print an optionally colorified test result
#
# The test will not be colored if
# 1) options.colored is False,
# 2) the environment variable BITTEN_NOCOLOR is true, or
# 3) the color parameter is False.
def printResult(test_name, result, timing, start, end, options, color=True):
  f_result = ''

  cnt = (TERM_COLS-2) - len(test_name + result)
  if color:
    f_result = test_name + '.'*cnt + ' ' + colorify(result, options)
  else:
    f_result = test_name + '.'*cnt + ' ' + result

  # Tack on the timing if it exists
  if timing:
    f_result += ' [' + '%0.3f' % float(timing) + 's]'
  if options.debug_harness:
    f_result += ' Start: ' + '%0.3f' % start + ' End: ' + '%0.3f' % end
  return f_result

## Color the error messages if the options permit, also do not color in bitten scripts because
# it messes up the trac output.
# supports weirded html for more advanced coloring schemes. <r>,<g>,<y>,<b> All colors are bolded.
def colorify(str, options, html=False):
  # ANSI color codes for colored terminal output
  RESET  = '\033[0m'
  BOLD   = '\033[1m'
  RED    = '\033[31m'
  GREEN  = '\033[32m'
  CYAN   = '\033[36m'
  YELLOW = '\033[33m'

  if options.colored and not (os.environ.has_key('BITTEN_NOCOLOR') and os.environ['BITTEN_NOCOLOR'] == 'true'):
    if html:
      str = str.replace('<r>', BOLD+RED)
      str = str.replace('<g>', BOLD+GREEN)
      str = str.replace('<y>', BOLD+YELLOW)
      str = str.replace('<b>', BOLD)
      str = re.sub(r'</[rgyb]>', RESET, str)
    else:
      str = str.replace('OK', BOLD+GREEN+'OK'+RESET)
      str = re.sub(r'(\[.*?\])', BOLD+CYAN+'\\1'+RESET, str)
      str = str.replace('skipped', BOLD+'skipped'+RESET)
      str = str.replace('deleted', BOLD+RED+'deleted'+RESET)
      if str.find('FAILED (EXODIFF)') != -1:
        str = str.replace('FAILED (EXODIFF)', BOLD+YELLOW+'FAILED (EXODIFF)'+RESET)
      elif str.find('FAILED (CSVDIFF') != -1:
        str = str.replace('FAILED (CSVDIFF)', BOLD+YELLOW+'FAILED (CSVDIFF)'+RESET)
      else:
        str = re.sub(r'(FAILED \([A-Za-z ]*\))', BOLD+RED+'\\1'+RESET, str)
  elif html:
    str = re.sub(r'</?[rgyb]>', '', str)    # strip all "html" tags

  return str


def getPlatforms():
  # We'll use uname to figure this out
  # Supported platforms are LINUX, DARWIN, SL, LION or ALL
  platforms = set()
  platforms.add('ALL')
  raw_uname = os.uname()
  if raw_uname[0].upper() == 'DARWIN':
    platforms.add('DARWIN')
    if re.match("10\.", raw_uname[2]):
      platforms.add('SL')
    if re.match("11\.", raw_uname[2]):
      platforms.add("LION")
  else:
    platforms.add(raw_uname[0].upper())
  return platforms

def getCompilers(libmesh_dir):
  # We'll use the GXX-VERSION string from LIBMESH's Make.common
  # to figure this out
  # Supported compilers are GCC, INTEL or ALL
  compilers = set()
  compilers.add('ALL')

  # Get the gxx compiler
  command = libmesh_dir + '/bin/libmesh-config --cxx'
  p = Popen(command, shell=True, stdout=PIPE)
  mpicxx_cmd = p.communicate()[0].strip()

  p = Popen(mpicxx_cmd + " --show", shell=True, stdout=PIPE)
  raw_compiler = p.communicate()[0]

  if re.search('icpc', raw_compiler) != None:
    compilers.add("INTEL")
  elif re.search('g\+\+', raw_compiler) != None:
    compilers.add("GCC")
  elif re.search('clang\+\+', raw_compiler) != None:
    compilers.add("CLANG")

  return compilers

def getPetscVersion(libmesh_dir):
  # We'll use PETSc's own header file to determine the PETSc version
  # (major.minor).  If necessary in the future we'll also detect subminor...
  #
  # Note: we used to find this info in Make.common, but in the
  # automake version of libmesh, this information is no longer stored
  # in Make.common, but rather in
  #
  # $LIBMESH_DIR/lib/${AC_ARCH}_${METHOD}/pkgconfig/Make.common.${METHOD}
  #
  # where ${AC_ARCH} is an architecture-dependent string determined by
  # libmesh's config.guess.  So we could try to look there, but it's
  # easier and more portable to look in ${PETSC_DIR}.

  # Default to something that doesn't make sense
  petsc_version_major = 'x'
  petsc_version_minor = 'x'

  # Get user's PETSC_DIR from environment.
  petsc_dir = os.environ.get('PETSC_DIR')

  # environ.get returns 'none' if no such environment variable exists.
  if petsc_dir == 'none':
    print "PETSC_DIR not found in environment!  Cannot detect PETSc version!"
    exit(1)

  # FIXME: handle I/O exceptions when opening this file
  f = open(petsc_dir + '/include/petscversion.h')

  # The version lines are (hopefully!) always going to be of the form
  # #define PETSC_VERSION_MAJOR      X
  # where X is some number, so in python, we can split the string and
  # pop the last substring (the version) off the end.
  for line in f.readlines():
    if line.find('#define PETSC_VERSION_MAJOR') != -1:
      petsc_version_major = line.split().pop()

    elif line.find('#define PETSC_VERSION_MINOR') != -1:
      petsc_version_minor = line.split().pop()

    # See if we're done.
    if (petsc_version_major != 'x' and petsc_version_minor != 'x'):
      break

  # Done with the file, so we can close it now
  f.close()

  # If either version was not found, then we can't continue :(
  if petsc_version_major == 'x':
    print("Error: could not determine valid PETSc major version.")
    exit(1)

  if petsc_version_minor == 'x':
    print("Error: could not determine valid PETSc minor version.")
    exit(1)

  petsc_version = petsc_version_major + '.' + petsc_version_minor

  # print "Running tests assuming PETSc version", petsc_version

  return petsc_version



def getParmeshOption(libmesh_dir):
  # Some tests work differently with parallel mesh enabled
  # We need to detect this condition
  parmesh = set()

  # We check libmesh_config.h for LIBMESH_ENABLE_PARMESH
  filenames = [
    libmesh_dir + '/include/base/libmesh_config.h',   # Old location
    libmesh_dir + '/include/libmesh/libmesh_config.h' # New location
    ];

  success = 0

  for filename in filenames:
    if success == 1:
      break

    try:
      f = open(filename)

      for line in f.readlines():
        m = re.search(r'#define\s+LIBMESH_ENABLE_PARMESH\s+(\d+)', line)
        if m != None:
          if m.group(1) == '1':
            parmesh.add('PARALLEL')
          else:
            parmesh.add('SERIAL')
          break

      f.close()
      success = 1

    except IOError, e:
      # print "Warning: I/O Error trying to read", filename, ":", e.strerror, "... Will try other locations."
      pass


  if success == 0:
    print "Error! Could not find libmesh_config.h in any of the usual locations!"
    exit(1)


  # If we didn't find the #define indicated by having no entries in our set, then parmesh is off
  if not len(parmesh):
    parmesh.add('SERIAL')
  parmesh.add('ALL')

  return parmesh





def getSharedOption(libmesh_dir):
  # Some tests may only run properly with shared libraries on/off
  # We need to detect this condition
  shared_option = set()
  shared_option.add('ALL')
  f = open(libmesh_dir + '/Make.common')
  for line in f.readlines():
    if line.find('enable-shared') != -1:
      m = re.search(r'=\s*(\S+)', line)
      if m != None:
        if m.group(1) == 'yes':
          shared_option.add('DYNAMIC')
        else:
          shared_option.add('STATIC')
        break
  f.close()
  return shared_option
