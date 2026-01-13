-- Seed Data for E-commerce Database

-- Insert users
INSERT INTO users (email, name, city, country) VALUES
('john@example.com', 'John Doe', 'Lagos', 'NG'),
('jane@example.com', 'Jane Smith', 'Abuja', 'NG'),
('mike@example.com', 'Mike Johnson', 'Lagos', 'NG'),
('sarah@example.com', 'Sarah Williams', 'Port Harcourt', 'NG'),
('david@example.com', 'David Brown', 'Abuja', 'NG');

-- Insert products
INSERT INTO products (name, description, price, category, stock_quantity) VALUES
('Laptop', 'High-performance laptop', 250000.00, 'Electronics', 50),
('Phone', 'Smartphone with great camera', 150000.00, 'Electronics', 100),
('Headphones', 'Wireless headphones', 25000.00, 'Electronics', 200),
('Desk Chair', 'Ergonomic office chair', 45000.00, 'Furniture', 30),
('Monitor', '27-inch 4K monitor', 120000.00, 'Electronics', 40),
('Keyboard', 'Mechanical keyboard', 35000.00, 'Electronics', 80),
('Mouse', 'Gaming mouse', 15000.00, 'Electronics', 150),
('Desk Lamp', 'LED desk lamp', 12000.00, 'Furniture', 60);

-- Insert orders
INSERT INTO orders (user_id, status, total) VALUES
(1, 'completed', 275000.00),
(1, 'completed', 150000.00),
(2, 'completed', 400000.00),
(3, 'pending', 45000.00),
(4, 'completed', 185000.00),
(5, 'completed', 120000.00),
(1, 'completed', 50000.00),
(2, 'completed', 27000.00);

-- Insert order items
INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
(1, 1, 1, 250000.00), (1, 3, 1, 25000.00),
(2, 2, 1, 150000.00),
(3, 1, 1, 250000.00), (3, 2, 1, 150000.00),
(4, 4, 1, 45000.00),
(5, 2, 1, 150000.00), (5, 6, 1, 35000.00),
(6, 5, 1, 120000.00),
(7, 3, 2, 50000.00),
(8, 8, 2, 24000.00), (8, 7, 1, 15000.00);
