import shutil
import subprocess


class FaspexCLI(object):

    def __init__(self, user, password, url, url_prefix='aspera/faspex', aspera_executable_path=None):
        self.user = user
        self.password = password
        self.url = url
        self.url_prefix = url_prefix
        self.aspera_executable_path = aspera_executable_path or shutil.which('aspera')

    def send_package(self):
        raise NotImplementedError

    def download_package_by_title(self, title):
        raise NotImplementedError

    def download_package_by_id(self, id_):
        raise NotImplementedError

    def _download_package(self):
        raise NotImplementedError

    def _parse_xml_response(self, xml):
        raise NotImplementedError

    def list_inbox_packages(self):
        return self._list_packages('inbox')

    def list_sent_packages(self):
        return self._list_packages('sent')

    def list_archived_packages(self):
        return self._list_packages('archived')

    def _list_packages(self, mailbox):
        if mailbox not in ['inbox', 'sent', 'archived']:
            raise ValueError('mailbox must be either inbox, sent, or archived')
        flags = ['--xml', '--{}'.format(mailbox)]
        cmd = self._build_cmd('list', flags)
        response, errors = self._call_faspex(cmd)
        return self._parse_xml_response(response)

    def _build_cmd(self, sub_command, flags=None):
        cmd = [self.aspera_executable_path, 'faspex', sub_command, '--host', self.url, '--username', self.user,
               '--password', self.password, '-U', self.url_prefix]
        if flags:
            cmd += flags
        return [str(i) for i in cmd]

    @staticmethod
    def _call_faspex(cmd):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=False
        )
        stdout, stderr = process.communicate()
        return stdout, stderr
