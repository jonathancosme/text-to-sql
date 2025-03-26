bash ./stop_db_server.sh
bash ./delete_db.sh
python ./make_fake_db_data.py
bash ./setup_postgres.sh
bash ./start_db_server.sh
python ./populate_db.py
