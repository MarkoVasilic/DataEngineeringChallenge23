# DataEngineeringChallenge23

## Data Processing (prepare_data.ipynb file)

1. First check was to see are all event ids unique in original dataset.
2. Second check was to see are all event types one of registration, transaction, login or logout.
3. Original dataset is used to create 3 tables, initial 3 tables are extracted from original dataset by using event type field. So in first table used rows are only ones with event type field with value registration, in second with value transaction, and third with values login or logout. Created tables are:
    * Registration - contains basic information about each user. All user_id are unique and that column is primary_key for this table. Columns in this table are:
        - user_id - UUID of user
        - name - name of user
        - country - two letters which represent country of user
        - date - date of registration
        - time - time of registration
        - device_os - operating system of device which is used to make an account
        - marketing_campaign - represents how user found about the game
    * Transaction - contains informations about each money transaction. All amounts are transfered to USD currency. Columns in this table are: 
        - user_id - UUID of user, this column is connected with user_id column of table Registration
        - transaction_currency - currency of transaction, all rows are USD
        - transaction_amount - amount used in transaction
        - transaction_id - unique id for each row, used as primary_key
    * Session - represents sessions of users in the game. In original dataset, it was noticed that there are cases where multiple events of login or logout events happend in a row for same user which doesn't make sense. In this table only first occurence in array of those events are kept, others are deleted. To form rows of this table with combined login and logout events, first initial table is sorted by user_id field and then by date and time of event. Then new rows are created by combining row with login event with next event that should be logout event. If for some user last event is login and not logut, than columns for logout are set to null. Columns in this table are:
        - user_id - UUID of user, this column is connected with user_id column of table Registration
        - login_date - date of login
        - login_time - time of login
        - logout_date - date of logout
        - logout_time - time of logout
        - duration_seconds - number of second between login and logout
        - session_id - unique id for each row, used as primary_key
4. Each created table is saved as csv file, which can be found in Data folder, but those files are not used in later processing.
5. Tables are saved to postgres sql database.

## FastAPI (main.py file)

1. Created connection with postgres sql
2. Made models for each table
3. Made response model for each of queries
4. Created functions which are responsible for handeling queries and returning requested values

## Instructions

1. Install libraries with command: 
    - pip install -r requirements.txt

2. The way how spark is setuped in this project is that there is wsl with ubuntu on windows 10. And in that ubuntu spark is installed and is configured so that when in terminal pyspark command is runned, jupyter notebook is opened in browser, in which spark is already running. So if you want to do it the same way this is command in terminal which you should run to be able to connect to postgres sql: 
    - pyspark --conf "spark.driver.extraClassPath=~/postgresql-42.6.0.jar" \
        --conf "spark.executor.extraClassPath=~/postgresql-42.6.0.jar" \
        --conf "spark.jars=~/postgresql-42.6.0.jar" \
        --conf "spark.driver.extraJavaOptions=-Duser.timezone=UTC" \
        --conf "spark.executor.extraJavaOptions=-Duser.timezone=UTC" \
        --packages org.postgresql:postgresql:42.6.0
3. There should be postgres sql installed in some way. In this project docker image of postgres is used with version 42.6.0. This is command to download and run docker image with same configuration used in this project: 
    - docker run --name some-postgres -e POSTGRES_PASSWORD=nordeus -p 5432:5432 -d postgres
4. In order to access fastapi, you should run next command in terminal:
    - uvicorn main:app --reload
5. Access this url in your browser: 
    - http://127.0.0.1:8000/docs
6. Run the queries. If you are using date parameter it should be in this format YYYY-MM-DD, user_id should be UUID, and country should be two letters upercase.

