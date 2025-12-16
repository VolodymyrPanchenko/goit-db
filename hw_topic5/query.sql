select * from orders;
SELECT 
    od.*,
    (
        SELECT o.customer_id
        FROM orders o
        WHERE o.id = od.order_id
    ) AS customer_id
FROM order_details od;

SELECT 
    od.*, 
    (
        SELECT o.shipper_id 
        FROM orders o 
        WHERE o.id = od.order_id
    ) AS shipper_id
FROM order_details od
WHERE od.order_id IN (
    SELECT id 
    FROM orders 
    WHERE shipper_id = 3
);
select order_id,AVG(quantity) from
	(select * from order_details od where od.quantity>10 ) as temp_table
group by order_id  

WITH TemporalTable AS (
    Select * 
    from order_details od 
    where od.quantity>10 
)
select order_id,AVG(quantity) 
FROM TemporalTable
GROUP BY order_id;  

DROP FUNCTION IF EXISTS CalculateDivide;

DELIMITER //

CREATE FUNCTION CalculateDivide(input_number1 FLOAT,input_number2 FLOAT)
RETURNS FLOAT
DETERMINISTIC 
NO SQL
BEGIN
    DECLARE result FLOAT;
    SET result = input_number1/input_number2;
    RETURN result;
END //

DELIMITER ;

Select quantity,CalculateDivide(quantity,2) as half_quantity from order_details
