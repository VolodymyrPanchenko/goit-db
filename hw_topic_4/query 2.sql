use mydb2;

SELECT 
    od.id AS order_detail_id,
    o.id AS order_id,
    c.name AS customer_name,
    p.name AS product_name,
    cat.name AS category_name,
    e.first_name AS employee_first_name,
    s.name AS shipper_name,
    sup.name AS supplier_name,
    od.quantity,
    p.price,
    o.date
FROM order_details od
INNER JOIN orders o 
    ON od.order_id = o.id
INNER JOIN customers c
    ON o.customer_id = c.id
INNER JOIN products p
    ON od.product_id = p.id
INNER JOIN categories cat
    ON p.category_id = cat.id
INNER JOIN employees e
    ON o.employee_id = e.employee_id
INNER JOIN shippers s
    ON o.shipper_id = s.id
INNER JOIN suppliers sup
    ON p.supplier_id = sup.id;

SELECT COUNT(*) AS total_rows
FROM order_details od
INNER JOIN orders o 
    ON od.order_id = o.id
INNER JOIN customers c
    ON o.customer_id = c.id
INNER JOIN products p
    ON od.product_id = p.id
INNER JOIN categories cat
    ON p.category_id = cat.id
INNER JOIN employees e
    ON o.employee_id = e.employee_id
INNER JOIN shippers s
    ON o.shipper_id = s.id
INNER JOIN suppliers sup
    ON p.supplier_id = sup.id;
    
    
SELECT COUNT(*)
FROM order_details od
LEFT JOIN orders o 
    ON od.order_id = o.id
LEFT JOIN customers c 
    ON o.customer_id = c.id
LEFT JOIN products p 
    ON od.product_id = p.id
LEFT JOIN categories cat 
    ON p.category_id = cat.id
LEFT JOIN employees e
    ON o.employee_id = e.employee_id
LEFT JOIN shippers s
    ON o.shipper_id = s.id
LEFT JOIN suppliers sup
    ON p.supplier_id = sup.id;


SELECT COUNT(*)
FROM order_details od
RIGHT JOIN orders o 
    ON od.order_id = o.id
RIGHT JOIN customers c 
    ON o.customer_id = c.id
RIGHT JOIN employees e
    ON o.employee_id = e.employee_id
RIGHT JOIN shippers s
    ON o.shipper_id = s.id
RIGHT JOIN products p 
    ON od.product_id = p.id
RIGHT JOIN suppliers sup 
    ON p.supplier_id = sup.id
RIGHT JOIN categories cat 
    ON p.category_id = cat.id;


SELECT 
    od.id AS order_detail_id,
    o.id AS order_id,
    c.name AS customer_name,
    p.name AS product_name,
    cat.name AS category_name,
    e.employee_id,
    e.first_name AS employee_first_name,
    s.name AS shipper_name,
    sup.name AS supplier_name,
    od.quantity,
    p.price,
    o.date
FROM order_details od
INNER JOIN orders o 
    ON od.order_id = o.id
INNER JOIN customers c
    ON o.customer_id = c.id
INNER JOIN products p
    ON od.product_id = p.id
INNER JOIN categories cat
    ON p.category_id = cat.id
INNER JOIN employees e
    ON o.employee_id = e.employee_id
INNER JOIN shippers s
    ON o.shipper_id = s.id
INNER JOIN suppliers sup
    ON p.supplier_id = sup.id
WHERE e.employee_id > 3
  AND e.employee_id <= 10;


SELECT 
    cat.name AS category_name,
    COUNT(*) AS rows_in_group,
    AVG(od.quantity) AS avg_quantity
FROM order_details od
INNER JOIN products p 
    ON od.product_id = p.id
INNER JOIN categories cat 
    ON p.category_id = cat.id
GROUP BY cat.name;

SELECT 
    cat.name AS category_name,
    COUNT(*) AS rows_in_group,
    AVG(od.quantity) AS avg_quantity
FROM order_details od
INNER JOIN products p 
    ON od.product_id = p.id
INNER JOIN categories cat 
    ON p.category_id = cat.id
GROUP BY cat.name
HAVING AVG(od.quantity) > 21;

SELECT 
    cat.name AS category_name,
    COUNT(*) AS rows_in_group,
    AVG(od.quantity) AS avg_quantity
FROM order_details od
INNER JOIN products p 
    ON od.product_id = p.id
INNER JOIN categories cat 
    ON p.category_id = cat.id
GROUP BY cat.name
HAVING AVG(od.quantity) > 21
ORDER BY rows_in_group DESC;

SELECT 
    cat.name AS category_name,
    COUNT(*) AS rows_in_group,
    AVG(od.quantity) AS avg_quantity
FROM order_details od
INNER JOIN products p 
    ON od.product_id = p.id
INNER JOIN categories cat 
    ON p.category_id = cat.id
GROUP BY cat.name
HAVING AVG(od.quantity) > 21
ORDER BY rows_in_group DESC
LIMIT 1, 4;

