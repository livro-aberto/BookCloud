from flask.views import View
from flask import render_template

class BaseView(View):
    """Base for all views
    """
    def __init__(self, view_name):
        self.view_name = view_name
        self.context = {}

    def dispatch_request(self):
        return self.get_response()

    def get_response(self):
        return render_template(self.template_name, **self.context)

    def make_template_context(self):
        self.context = {
            'menu_bar': {},
            'view': self.view_name
        }
