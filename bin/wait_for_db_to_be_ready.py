"""Grabs tickets from csv and makes process instances."""
import time

import sqlalchemy
from flask_bpmn.models.db import db

from spiffworkflow_backend import get_hacked_up_app_for_script


def try_to_connect(start_time: float) -> None:
    """Try to connect."""
    try:
        db.first_or_404("select 1")
    except sqlalchemy.exc.DatabaseError as exception:
        if time.time() - start_time > 15:
            raise exception
        else:
            time.sleep(1)
            try_to_connect(start_time)


def main() -> None:
    """Main."""
    app = get_hacked_up_app_for_script()
    start_time = time.time()
    with app.app_context():
        try_to_connect(start_time)


if __name__ == "__main__":
    main()
