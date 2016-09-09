# imports for tornado
import tornado
from tornado import web, httpserver, ioloop

# imports for logging
import traceback
import os
from os import path

# imports for yara to work
from io import StringIO
import base64
import yara

# imports for services
from holmeslibrary.services import ServiceConfig

# Get service meta information and configuration
Config = ServiceConfig("./service.conf")

Metadata = {
    "Name"        : "Yara",
    "Version"     : "1.0",
    "Description" : "./README.md",
    "Copyright"   : "Copyright 2016 Holmes Group LLC",
    "License"     : "./LICENSE"
}

class YaraHandler(tornado.web.RequestHandler):
    @property
    def YaraEngine(self):
        return yara.load(Config.yara_rules.local_path)

class YaraProcess(YaraHandler):
    def process(self, filename, rules=None):
        try:
            if rules:
                ruleBuff = StringIO()
                ruleBuff.write(rules)
                ruleBuff.seek(0)
                rules = yara.load(file=ruleBuff)
                results = rules.match(filename[0], externals={'filename': filename[1]})
            else:
                results = self.YaraEngine.match(filename[0], externals={'filename': filename[1]})
            results2 = list(map(lambda x: {"rule": x.rule}, results))
            return results2
        except Exception as e:
            return e

    def get(self, filename):
        try:
            fullPath = (os.path.join('/tmp/', filename), filename)
            data = self.process(fullPath)
            self.write({"yara": data})
        except Exception as e:
            self.write({"error": traceback.format_exc(e)})

    def post(self, filename):
        try:
            fullPath = os.path.join('/tmp/', filename)
            rules = base64.b64decode(self.get_body_argument('custom_rule')).decode('latin-1')
            data = self.process(fullPath, rules)
            self.write({"yara": data})
        except Exception as e:
            self.write({"error": traceback.format_exc(e)})


class Info(tornado.web.RequestHandler):
    # Emits a string which describes the purpose of the analytics
    def get(self):
        info = """
            <p>{name:s} - {version:s}</p>
            <hr>
            <p>{description:s}</p>
            <hr>
            <p>{license:s}
        """.format(
            name        = str(Metadata["Name"]).replace("\n", "<br>"),
            version     = str(Metadata["Version"]).replace("\n", "<br>"),
            description = str(Metadata["Description"]).replace("\n", "<br>"),
            license     = str(Metadata["License"]).replace("\n", "<br>")
        )
        self.write(info)


class YaraApp(tornado.web.Application):
    def __init__(self):

        for key in ["Description", "License"]:
            fpath = Metadata[key]
            if os.path.isfile(fpath):
                with open(fpath) as file:
                    Metadata[key] = file.read()

        handlers = [
            (r'/', Info),
            (r'/analyze/([a-zA-Z0-9\-\.]*)', YaraProcess),
        ]
        settings = dict(
            template_path=path.join(path.dirname(__file__), 'templates'),
            static_path=path.join(path.dirname(__file__), 'static')
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        self.engine = None


def main():
    server = tornado.httpserver.HTTPServer(YaraApp())
    server.listen(Config.settings.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
