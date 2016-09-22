import os
from seqc import log, io, exceptions, remote
from seqc.core import verify
from math import ceil
from warnings import warn


class local_instance_cleanup:

    def __init__(self, args):
        """Execute the seqc code on an instance with defined cleanup practices"""
        self.args = args
        self.err_status = False
        self.email = verify.executables('mutt')[0]  # unpacking necessary for singleton
        self.aws_upload_key = args.output_stem

    def __enter__(self):
        """No entrance behavior is necessary to wrap the main function"""
        return

    def __exit__(self, exc_type, exc_val, exc_tb):
        """If an exception occurs, log the exception, email if possible, then terminate
        the aws instance if requested by the user

        :param exc_type: type of exception encountered
        :param exc_val: value of exception
        :param exc_tb: exception traceback
        """

        # log any non-SystemExit exceptions if they were encountered, and email user if
        # specified in args.
        if issubclass(exc_type, Exception):
            log.exception()
            self.err_status = True  # we have encountered an error
            if self.args.email_status and self.email:
                email_body = 'Process interrupted -- see attached error message'
                if self.args.aws:
                    attachment = '/data/' + self.args.log_name
                else:
                    attachment = self.args.log_name
                if self.aws_upload_key:
                    bucket, key = io.S3.split_link(self.aws_upload_key)
                    exceptions.retry_boto_call(io.S3.upload_file)(
                        attachment, bucket, key)
                remote.email_user(attachment=attachment, email_body=email_body,
                                  email_address=self.args.email_status)

        # determine if instance needs clean up
        if self.args.remote:
            return True  # this is a remote run, there is no instance to terminate.

        # determine how to deal with termination in the event of errors
        if self.args.no_terminate == 'on-success':
            if self.err_status:
                no_terminate = 'True'
            else:
                no_terminate = 'False'
        else:
            no_terminate = self.args.no_terminate

        if no_terminate in ['False', 'false']:
            fpath = '/data/instance.txt'
            if os.path.isfile(fpath):
                with open(fpath, 'r') as f:
                    inst_id = f.readline().strip('\n')
                remote.terminate_cluster(inst_id)
            else:
                log.info('File containing instance id is unavailable!')
        else:
            log.info('no-terminate={}; cluster not terminated. User is responsible for '
                     'clean-up'.format(self.args.no_terminate))

        return True  # signals successful cleanup for contextmanager


class remote_execute:

    def __init__(self, instance_type=None, spot_bid=None, volsize=None):
        """Create a temporary cluster for the remote execution of passed command strings

        :param instance_type:
        :param spot_bid:
        :param volsize:
        """

        self.instance_type = instance_type
        self.spot_bid = spot_bid
        self.volsize = int(ceil(volsize / 1e9))
        self.cluster = None
        self.async_process = False

    def __enter__(self):
        """create a cluster and make it accessible within the context"""
        try:
            cluster = remote.ClusterServer()
            cluster.setup_cluster(
                self.volsize, self.instance_type, spot_bid=self.spot_bid)
            cluster.serv.connect()
            self.cluster = cluster
        except Exception as e:
            log.notify('Exception {e} occurred during cluster setup!'.format(e=e))
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """terminate the instance unless a clean asynchronous call was made"""

        if exc_type or not self.async_process:
            log.notify('%s: %s\n%s' % (exc_type, exc_val, exc_tb))
            self.cluster.serv.disconnect()
            remote.terminate_cluster(self.cluster.inst_id.instance_id)
        return True  # signal clean exit

    def execute(self, command_string):
        """run the remote function on the server, capturing output and errors"""
        data, errs = self.cluster.serv.exec_command(command_string)
        if errs:
            raise ChildProcessError(errs)
        return data

    def async_execute(self, command_string):
        """run the remote function on the server, signaling to remote_execute that there
        may be a process that remains running in the background after this function
        returns.

        If an async_execute function returns without error, instance termination is
        halted, and the user must manually terminate the instance with
        "SEQC.py instance terminate -i <instance id>"

        :param command_string: command to be remote executed. Assumed to be called with
          nohup, to prevent hangup when the ssh shell is disconnected, and to be placed
          in the background with "&", so that async_execute() returns immediately. If
          these requirements are not met, there may be undefined results, and the
          process will warn the user.
        """
        if not all((s in command_string for s in ['nohup', '&'])):
            warn('Excecuting command that may not be asynchronous. User is '
                 'responsible for including commands that place the called function '
                 'into the background. Missing "nohup" or "&". If a synchronous command '
                 'is desired, please use the execute() method.')
        self.cluster.serv.exec_command(command_string)
        self.async_process = True

    def put_file(self, local_file, remote_file):
        self.cluster.serv.put_file(local_file, remote_file)

    def get_file(self, remote_file, local_file):
        self.cluster.serv.get_file(remote_file, local_file)