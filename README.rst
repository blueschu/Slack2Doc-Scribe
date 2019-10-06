Slack2Docs Scribe
=================

A simple Flask app to log Slack messages to a Google Docs document for permanent and accessible storage.

Installation
------------

Before installing Slack2Docs Scribe, we recommended that you create a virtual environment to keep your system-wide Python environment clean. If you are using Python 3.6 or greater, the tools you will to create virtual environments ship with the interpreter as the `venv`_ module.

.. _venv: https://docs.python.org/3.6/library/venv.html

To install the latest and greatest release of Slack2Docs Scribe, run the following pip command:

.. code-block:: shell

    $ pip install git+https://github.com/gstrenge/Slack2Doc-Scribe.git

TODO: Detail slack app creation.

Configuration
-------------

To configure the behavior of this app, create a JSON file that contains the following keys:

- ``signing_secret`` - The signing secret for your Slack App.
- ``channels`` - A list of slack channels that you want this app to monitor.
- ``doc_id`` - The ID of the Google Sheets spreadsheet that this app can write to.
- ``endpoint`` - The URI that this app will be served from.
- ``log_file`` - The path to the file that this app should write log entries to.
- ``api_token`` - The API Token for your Slack App.

In order for Slack2Docs Scribe to discover your configuration file, you must set the ``FLASK_SETTINGS_SECRETS`` environment variable to be your configuration file's path.

Running the App
---------------

Running with CGI
^^^^^^^^^^^^^^^^

CGI support is available on almost every webserver and can usually be configured from by unprivileged user. Due note, however, that there are numerous drawbacks from using CGI instead of a more modern protocol such as WSGI or FastCGI.

To run this app using CGI, start by creating a ``.cgi`` application file. We'll call it ``app.cgi``:

.. code-block:: python

    #!/usr/bin/env python3

    import os
    from wsgiref.handlers import GCIHandler

    # Optional - You may remove this line if the FLASK_SETTINGS_SECRETS variable
    # is already set in your environment.
    os.environ.setdefault('FLASK_SETTINGS_SECRETS', '/path/to/your/secrets/file.json')

    import slack2doc

    if __name__ == '__main__':
        app = slack2doc.create_app()
        CGIHandler().run(app)

Next, you will need to configure your webserver to run the CGI script. For Apapche, you have two options:

1. Add a ``ScriptAlias`` to your Apache configuration that points to the CGI file you just created
2. Place your CGI file directly in your webserver's document root

For more information about how to configure CGI in Apache, see `Apache's CGI Tutorial`_.

.. _Apache's CGI Tutorial: https://httpd.apache.org/docs/2.4/howto/cgi.html


Running with WSGI, FastCGI, or uWSGI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Slack2Docs Scribe is, at its heart, a Flask app, and so it can be deployed in the same ways that any Flask app can be. For details on how to deploy Slack2Docs Scribe with WSGI, FastCGI, or uWSGI, see Flask's `Deployment Options documentation`_.

.. _Deployment Options documentation: https://flask.palletsprojects.com/en/1.1.x/deploying/
