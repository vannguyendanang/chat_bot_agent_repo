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
-- Table structure for table `bankaccount`
--

DROP TABLE IF EXISTS `bankaccount`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bankaccount` (
  `AccountNumber` varchar(255) NOT NULL,
  `Password` varchar(100) DEFAULT NULL,
  `FirstName` varchar(255) DEFAULT NULL,
  `LastName` varchar(255) DEFAULT NULL,
  `Email` varchar(255) DEFAULT NULL,
  `DoB` date DEFAULT NULL,
  `PhoneNumber` varchar(255) DEFAULT NULL,
  `Address` varchar(255) DEFAULT NULL,
  `SSN` varchar(150) DEFAULT NULL,
  `AccBalance` int DEFAULT NULL,
  PRIMARY KEY (`AccountNumber`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bankaccount`
--

LOCK TABLES `bankaccount` WRITE;
/*!40000 ALTER TABLE `bankaccount` DISABLE KEYS */;
INSERT INTO `bankaccount` VALUES ('3423346','12234','Mary','Jones','st_123_marry@gmail.com','1993-09-15','2014562316','1617 13th Ave S AptC, Birmingham, Alabama, 35205','S96345A4345',2000),('3423347','12235','John','Smith','new_john@gmail.com','1998-08-16','2064562317','1454 14th Ave S AptA, Birmingham, Alabama, 35205','S96345A4346',3000),('3423348','12236','Robert','Williams','robert@gmail.com','1963-12-17','2074562318','8036 Darby Place, Reseda, CA 91335','S96345B4347',5200),('3423349','12237','Patricia','Brown','patricia@gmail.com','1982-07-18','2054562319','4357 15th Ave S, Birmingham, Alabama, 35205','S96345C4348',14000),('3423350','12238','James','Miller','james@gmail.com','1987-12-19','2014562320','3000 12th Ave S, Birmingham, Alabama, 35205','S96345A4349',34000),('3423351','12239','Linda','Davis','linda_update@gmail.com','1991-03-20','2054562321','9436 Darby Place, Reseda, CA 91335','S96345N4350',5000),('3423352','12240','Michael','Wilson','michael@gmail.com','1974-06-21','2084562322','9437 Darby Place, Reseda, CA 91335','S96345A4351',790),('3423353','12241','Susan','Garcia','susan@gmail.com','1978-11-22','2054562323','9438 Darby Place, Reseda, CA 91335','S96345A4352',556);
/*!40000 ALTER TABLE `bankaccount` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-27 14:36:59
