-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: 31.11.38.14:3306
-- Creato il: Feb 05, 2026 alle 11:49
-- Versione del server: 8.0.43-34
-- Versione PHP: 8.0.7

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `Sql1905550_1`
--

-- --------------------------------------------------------

--
-- Struttura della tabella `Alerts`
--

CREATE TABLE `Alerts` (
  `ID` int UNSIGNED NOT NULL,
  `fridge_ID` int UNSIGNED NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `category` enum('door_open','door_closed','door_left_open','high_temp','critic_temp','low_temp','critic_power','sensor_offline') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `message` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Trigger `Alerts`
--
DELIMITER $$
CREATE TRIGGER `cleanup_old_alerts` AFTER INSERT ON `Alerts` FOR EACH ROW BEGIN
 IF (NEW.ID % 50) = 0 THEN
        DELETE FROM Alerts
        WHERE fridge_ID = NEW.fridge_ID
          AND timestamp < NOW() - INTERVAL 7 DAY
        LIMIT 500;
    END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Struttura della tabella `Fridges`
--

CREATE TABLE `Fridges` (
  `ID` int UNSIGNED NOT NULL,
  `user_ID` int UNSIGNED DEFAULT NULL,
  `position` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Struttura della tabella `Measurements`
--

CREATE TABLE `Measurements` (
  `ID` int UNSIGNED NOT NULL,
  `fridge_ID` int UNSIGNED NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `temperature` decimal(3,1) NOT NULL COMMENT 'celsius',
  `power` decimal(7,2) NOT NULL COMMENT 'watt'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Trigger `Measurements`
--
DELIMITER $$
CREATE TRIGGER `alert_critic_power` AFTER INSERT ON `Measurements` FOR EACH ROW BEGIN
	IF NEW.power < 0.0 OR NEW.power > 10000.0 THEN
   		SIGNAL SQLSTATE '45000'
    	SET MESSAGE_TEXT = 'Potenza fuori range valido (0-10000W)';
	END IF;

    IF NEW.power > 500.00 THEN 
        INSERT INTO Alerts (fridge_ID, timestamp, category, message)
        VALUES (NEW.fridge_ID, NEW.timestamp, 'critic_power', 
                CONCAT('POTENZA CRITICA: ', NEW.power, 'W ATTENZIONE'));
    END IF;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `alert_temperature` AFTER INSERT ON `Measurements` FOR EACH ROW BEGIN
-- Temperatura anomala
	IF NEW.temperature < -40.0 OR NEW.temperature > 60.0 THEN
    	SIGNAL SQLSTATE '45000'
    	SET MESSAGE_TEXT = 'Temperatura fuori range valido';
	END IF;

 -- Temperatura troppo BASSA (di norma <0°C = rischio congelamento)
    IF NEW.temperature < 12.0 THEN
        INSERT INTO Alerts (fridge_ID, timestamp, category, message)
        VALUES (NEW.fridge_ID, NEW.timestamp, 'low_temp', 
                CONCAT('Temperatura troppo bassa: ', NEW.temperature, '°C (zona congelamento)'));
    END IF;

 -- Zona GIALLA: Warning (di norma 6-8°C)
    IF NEW.temperature > 20.0 AND NEW.temperature <= 25.0 THEN
        INSERT INTO Alerts (fridge_ID, timestamp, category, message)
        VALUES (NEW.fridge_ID, NEW.timestamp, 'high_temp', 
                CONCAT('Temperatura elevata: ', NEW.temperature, '°C (zona warning)'));
    END IF;
    
    -- Zona ROSSA: Pericolo (di norma >8°C)
    IF NEW.temperature > 25.0 THEN
        INSERT INTO Alerts (fridge_ID, timestamp, category, message)
        VALUES (NEW.fridge_ID, NEW.timestamp, 'critic_temp', 
                CONCAT('TEMPERATURA CRITICA: ', NEW.temperature, '°C (zona pericolo)'));
    END IF;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `cleanup_old_measurements` AFTER INSERT ON `Measurements` FOR EACH ROW BEGIN

	IF (NEW.ID % 100) = 0 THEN
    	DELETE FROM Measurements
   		WHERE fridge_ID = NEW.fridge_ID
    		AND TIMESTAMP < NOW() - INTERVAL 48 HOUR
    	LIMIT 1000;
	END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Struttura della tabella `Products`
--

CREATE TABLE `Products` (
  `ID` int UNSIGNED NOT NULL,
  `name` varchar(50) NOT NULL,
  `brand` varchar(50) DEFAULT NULL,
  `category` enum('meat','fish','dairy','vegetables','bread','other') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'other'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Struttura della tabella `ProductsFridge`
--

CREATE TABLE `ProductsFridge` (
  `ID` int UNSIGNED NOT NULL,
  `fridge_ID` int UNSIGNED NOT NULL,
  `product_ID` int UNSIGNED NOT NULL,
  `quantity` int UNSIGNED NOT NULL DEFAULT '1',
  `added_in` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `removed_in` timestamp NULL DEFAULT NULL
) ;

-- --------------------------------------------------------

--
-- Struttura della tabella `ProductsMovements`
--

CREATE TABLE `ProductsMovements` (
  `ID` int UNSIGNED NOT NULL,
  `fridge_ID` int UNSIGNED NOT NULL,
  `product_ID` int UNSIGNED NOT NULL,
  `quantity` int NOT NULL COMMENT 'positive = added;\r\n\r\n\r\nnegative = removed',
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Trigger `ProductsMovements`
--
DELIMITER $$
CREATE TRIGGER `update_product_quantity` AFTER INSERT ON `ProductsMovements` FOR EACH ROW BEGIN
 INSERT INTO ProductsFridge (fridge_ID, product_ID, quantity, added_in)
    VALUES (NEW.fridge_ID, NEW.product_ID, NEW.quantity, NEW.timestamp)
    ON DUPLICATE KEY UPDATE 
        quantity = quantity + NEW.quantity,
        removed_in = IF(quantity + NEW.quantity = 0, NEW.timestamp, NULL);
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Struttura della tabella `Users`
--

CREATE TABLE `Users` (
  `ID` int UNSIGNED NOT NULL,
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Indici per le tabelle scaricate
--

--
-- Indici per le tabelle `Alerts`
--
ALTER TABLE `Alerts`
  ADD PRIMARY KEY (`ID`),
  ADD KEY `idx_timestamp` (`timestamp` DESC),
  ADD KEY `idx_category` (`fridge_ID`,`category`,`timestamp` DESC),
  ADD KEY `fk_alerts_fridge` (`fridge_ID`);

--
-- Indici per le tabelle `Fridges`
--
ALTER TABLE `Fridges`
  ADD PRIMARY KEY (`ID`),
  ADD KEY `fk_fridges_user` (`user_ID`);

--
-- Indici per le tabelle `Measurements`
--
ALTER TABLE `Measurements`
  ADD PRIMARY KEY (`ID`),
  ADD KEY `idx_measurements_time` (`fridge_ID`,`timestamp` DESC),
  ADD KEY `idx_timestamp` (`timestamp` DESC),
  ADD KEY `idx_power` (`fridge_ID`,`power` DESC);

--
-- Indici per le tabelle `Products`
--
ALTER TABLE `Products`
  ADD PRIMARY KEY (`ID`),
  ADD KEY `idx_product_name` (`name`);

--
-- Indici per le tabelle `ProductsFridge`
--
ALTER TABLE `ProductsFridge`
  ADD PRIMARY KEY (`ID`),
  ADD UNIQUE KEY `idx_fridge_product` (`fridge_ID`,`product_ID`) USING BTREE,
  ADD KEY `fk_productsfridge_product` (`product_ID`),
  ADD KEY `fk_productsfridge_fridge` (`fridge_ID`),
  ADD KEY `idx_removed` (`fridge_ID`,`removed_in`);

--
-- Indici per le tabelle `ProductsMovements`
--
ALTER TABLE `ProductsMovements`
  ADD PRIMARY KEY (`ID`),
  ADD KEY `idx_movements_time` (`fridge_ID`,`timestamp` DESC),
  ADD KEY `fk_product` (`product_ID`);

--
-- Indici per le tabelle `Users`
--
ALTER TABLE `Users`
  ADD PRIMARY KEY (`ID`),
  ADD UNIQUE KEY `unique_email` (`email`);

--
-- AUTO_INCREMENT per le tabelle scaricate
--

--
-- AUTO_INCREMENT per la tabella `Alerts`
--
ALTER TABLE `Alerts`
  MODIFY `ID` int UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT per la tabella `Fridges`
--
ALTER TABLE `Fridges`
  MODIFY `ID` int UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT per la tabella `Measurements`
--
ALTER TABLE `Measurements`
  MODIFY `ID` int UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT per la tabella `Products`
--
ALTER TABLE `Products`
  MODIFY `ID` int UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT per la tabella `ProductsFridge`
--
ALTER TABLE `ProductsFridge`
  MODIFY `ID` int UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT per la tabella `ProductsMovements`
--
ALTER TABLE `ProductsMovements`
  MODIFY `ID` int UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT per la tabella `Users`
--
ALTER TABLE `Users`
  MODIFY `ID` int UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Limiti per le tabelle scaricate
--

--
-- Limiti per la tabella `Alerts`
--
ALTER TABLE `Alerts`
  ADD CONSTRAINT `fk_alerts_fridge` FOREIGN KEY (`fridge_ID`) REFERENCES `Fridges` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Limiti per la tabella `Fridges`
--
ALTER TABLE `Fridges`
  ADD CONSTRAINT `fk_fridges_user` FOREIGN KEY (`user_ID`) REFERENCES `Users` (`ID`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Limiti per la tabella `Measurements`
--
ALTER TABLE `Measurements`
  ADD CONSTRAINT `fk_measurements_fridge` FOREIGN KEY (`fridge_ID`) REFERENCES `Fridges` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Limiti per la tabella `ProductsFridge`
--
ALTER TABLE `ProductsFridge`
  ADD CONSTRAINT `fk_productsfridge_fridge` FOREIGN KEY (`fridge_ID`) REFERENCES `Fridges` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_productsfridge_product` FOREIGN KEY (`product_ID`) REFERENCES `Products` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Limiti per la tabella `ProductsMovements`
--
ALTER TABLE `ProductsMovements`
  ADD CONSTRAINT `fk_fridge` FOREIGN KEY (`fridge_ID`) REFERENCES `Fridges` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_product` FOREIGN KEY (`product_ID`) REFERENCES `Products` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
