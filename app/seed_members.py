"""One-time seed script for initial members."""
from app import db
from app.models.member import Member


INITIAL_MEMBERS = [
    ('Mike Wallin', 'michaelwallin@hotmail.com'),
    ('LDS Duray', 'ldsduray@aol.com'),
    ('Steve Dahl', 'srdahl@pnwr.com'),
    ('Wesley Johnson', 'wesj3@comcast.net'),
    ('Andrew Hamilton', 'andyham@comcast.net'),
    ('Scott', '7rvydra@gmail.com'),
    ('Matthew Andersen', 'mjandersen@walstead.com'),
    ('Steve Waite', 'steve@waitespecialty.com'),
    ('David Nelson', 'nelsonlawfirm@me.com'),
    ('Dave Spurgeon', 'davespurgeon@yahoo.com'),
    ('Casey Heaton', 'casey@candrtractor.com'),
    ('Vince Penta', 'vincepenta@vlplaw.net'),
    ('D Petersen', 'dpetersen@centurylink.net'),
    ('Gareth Penta', 'garethpenta@gmail.com'),
    ('Shawn Marvin', 'shawndmarvin@yahoo.com'),
    ('Randy Walker', 'randy@kr-consultants.com'),
    ('Josh Johnson', 'caellwyn@gmail.com'),
]


def seed_members():
    """Add initial members if they don't exist. Returns summary."""
    added = 0
    skipped = 0
    
    for name, email in INITIAL_MEMBERS:
        existing = Member.query.filter_by(email=email).first()
        if not existing:
            member = Member(name=name, email=email, member_type='regular')
            db.session.add(member)
            added += 1
        else:
            skipped += 1
    
    db.session.commit()
    total = Member.query.count()
    
    return {
        'added': added,
        'skipped': skipped,
        'total': total
    }
