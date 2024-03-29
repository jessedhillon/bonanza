import transaction
from unittest import TestCase

from pyramid import testing

from bonanza.lib.models.meta import Session

class TestMyView(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from bonanza.lib..models import Model
        Session.configure(bind=engine)
        Base.metadata.create_all(engine)
        with transaction.manager:
            model = Model(name='one', value=55)
            Session.add(model)

    def tearDown(self):
        Session.remove()
        testing.tearDown()

    def test_it(self):
        from .views import my_view
        request = testing.DummyRequest()
        info = my_view(request)
        self.assertEqual(info['one'].name, 'one')
        self.assertEqual(info['project'], 'bonanza')
