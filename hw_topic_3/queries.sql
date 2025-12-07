SELECT * from products;
SELECT name, phone FROM shippers;

SELECT AVG(price) AS avg_price, MIN(price) as min_price, MAX(price) as max_price 
FROM products;

SELECT DISTINCT category_id, price
FROM products
ORDER BY price DESC
LIMIT 10;

SELECT COUNT(*)
FROM products
WHERE price BETWEEN 20 AND 100;

SELECT supplier_id, AVG(price), COUNT(*)
FROM products
GROUP BY supplier_id;