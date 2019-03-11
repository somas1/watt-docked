from watt_app.extensions import db


class Events(db.Model):
    timestamp = db.Column(db.DateTime, primary_key=True)
    watts = db.Column(db.Float, index=True)
    watthours = db.Column(db.Float)

    def __repr__(self):
        return 'Watts:{}, Watthours:{}, \
        Time:{}'.format(self.watts, self.watthours, self.timestamp)
