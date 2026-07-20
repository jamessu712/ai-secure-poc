# Threat Model (STRIDE)

## Spoofing
Mitigated by Azure AD Managed Identity

## Tampering
Data processed immutably post-masking

## Repudiation
Azure Activity Logs retained

## Information Disclosure
- No public endpoints
- PII removed before storage

## Denial of Service
POC scope only, throttled SKUs

## Elevation of Privilege
RBAC least-privilege enforced
