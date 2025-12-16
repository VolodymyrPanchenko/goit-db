SELECT
    id,
    date,
    YEAR(date)  AS year,
    MONTH(date) AS month,
    DAY(date)   AS day
FROM orders;

SELECT
    id,
    date,
    date + INTERVAL 1 DAY AS date_plus_one_day
FROM orders;

SELECT
    id,
    date,
    UNIX_TIMESTAMP(date) AS date_timestamp
FROM orders;

SELECT count(*)
FROM orders
WHERE date BETWEEN '1996-07-10 00:00:00' AND '1996-10-08 00:00:00';

DROP FUNCTION IF EXISTS CreateJSON;
DELIMITER //

CREATE FUNCTION CreateJSON(p_id INT, p_date DATE)
RETURNS json
DETERMINISTIC 
NO SQL
BEGIN
    DECLARE result json;
    SET result = JSON_OBJECT('id', p_id, 'date', p_date);
    RETURN result;
END //

DELIMITER ;

SELECT  id, date, CreateJSON(id,date)
FROM orders;
SELECT CreateJSON(87, '1996-07-10');