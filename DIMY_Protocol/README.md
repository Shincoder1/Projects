# DIMY Digital Contact Tracing Protocol

This project implements the DIMY Digital Contact Tracing Protocol, a decentralized system for contact tracing and risk analysis of COVID-19 using a combination of Diffie-Hellman key exchange, secret sharing, and Bloom filters. The system is designed to help track potential exposure to COVID-19 while maintaining user privacy.

## Overview

The DIMY protocol facilitates the generation and exchange of ephemeral identifiers (Ephemeral ID, EphID) between devices. These identifiers are used to establish a shared secret key (Encounter ID, EncID) that is used to record encounters between devices. Devices store these encounters in Bloom filters, which are later used to check if a device has been in close contact with someone diagnosed with COVID-19.

### Key Features

1. **Ephemeral Identifiers (EphID)**: Devices generate random EphIDs periodically.
2. **Secret Sharing**: EphIDs are split into multiple shares using the Shamir Secret Sharing scheme.
3. **Diffie-Hellman Key Exchange**: Devices perform key exchange to calculate a shared secret (EncID).
4. **Bloom Filters**: Encounters are recorded in Daily Bloom Filters (DBF) and Query Bloom Filters (QBF) for efficient matching.
5. **Backend Server**: A centralized backend server (TCP server) receives the Contact Bloom Filter (CBF) and performs risk analysis.
6. **Risk Analysis**: The backend server matches the QBF uploaded by a device with CBFs stored in the server to notify the device of any potential exposure.

## Installation
1. cryptography
2. bloom-filter
3. subrosa
4. bitarray

### Clone the repository:

```bash
git clone <repository_url>
cd dimy-protocol
