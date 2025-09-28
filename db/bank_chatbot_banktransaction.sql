-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: localhost    Database: bank_chatbot
-- ------------------------------------------------------
-- Server version	8.0.41

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `banktransaction`
--

DROP TABLE IF EXISTS `banktransaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `banktransaction` (
  `TransactionId` varchar(255) NOT NULL,
  `AccountNumber` varchar(100) DEFAULT NULL,
  `ReceiverFirstName` varchar(255) DEFAULT NULL,
  `ReceiverLastName` varchar(255) DEFAULT NULL,
  `TransDateTime` datetime DEFAULT NULL,
  `TransferContent` varchar(255) DEFAULT NULL,
  `TransferStatus` varchar(50) DEFAULT NULL,
  `TransferAmount` int DEFAULT NULL,
  PRIMARY KEY (`TransactionId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `banktransaction`
--

LOCK TABLES `banktransaction` WRITE;
/*!40000 ALTER TABLE `banktransaction` DISABLE KEYS */;
INSERT INTO `banktransaction` VALUES ('2367','3423346','Brooks','Alvarez','2025-06-01 15:45:30','order food','Sent',120),('2368','3423346','Watson','Castillo','2025-05-04 13:00:30','buy groceries','Disputed',345),('2369','3423346','Bennet','Sanders','2025-05-05 13:00:30','purchase flight ticket','Pending',611),('2370','3423346','Gray','Patel','2025-08-25 10:00:30','deposit for rental','Disputed',535),('2371','3423350','Mendoza','Myers','2025-10-25 11:00:30','study tuition','Sent',798),('2372','3423350','Hughes','Long','2025-04-26 06:00:30','cinema tickets','Sent',124),('2373','3423350','Gray','Patel','2025-02-27 09:00:30','travel cost','Pending',5000),('2374','3423350','Hughes','Long','2025-04-28 11:00:30','hotel payment','Sent',389),('2375','3423350','Watson','Castillo','2025-11-29 20:00:30','car rental','Sent',444),('2376','3423350','Bennet','Sanders','2025-10-30 11:45:30','buy new shoes','Sent',32),('2377','3423350','Mendoza','Myers','2025-12-31 11:30:30','eat at restaurant','Sent',45);
/*!40000 ALTER TABLE `banktransaction` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-27 14:37:00
