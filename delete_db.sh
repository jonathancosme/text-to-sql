pg_ctl -D ./pgdata stop

rm -r -f ./pgdata
rm -f db_config.env
rm -f logfile
rm ./table_csvs/*.csv