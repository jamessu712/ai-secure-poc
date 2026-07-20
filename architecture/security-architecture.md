# AI POC Security Architecture

## Overview
This POC implements a secure-by-design AI architecture on Azure, ensuring
data privacy, least-privilege access, and network isolation.

## Key Principles
- Zero Trust
- No Public Network Access
- No Secrets or Keys
- Data Minimization & Irreversibility

## Components
- Azure Blob Storage (Private Endpoint)
- Azure AI Search (Vector Index, Private)
- Azure Cognitive Services (PII Detection)
- Azure Functions (Masking & Tokenization)
- Azure Key Vault (Salt storage)
- VNet with dedicated subnets

## Data Flow
Raw Data → PII Detection → Masking/Pseudonymization → Clean Data → Vector Index

## Security Guarantees
- PII never stored in vector database
- Embeddings are non-reversible
- Managed Identity for all access
- Full logical & network isolation from production
