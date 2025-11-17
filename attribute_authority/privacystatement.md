# Attribute Authority privacy policy and description

## Description of the service
The Attribute Authority provides a layer where identities, enrollment, group membership, and other attributes and authorization policies on distributed resources can be managed in a homogeneous way. It acts as a central service for authentication and authorization management for linked Helmholtz / KIT services.

## Processed data
The following OIDC scopes are requested from the Identity / OIDC Provider:
- openid
- profile
- email (if available)

Example of released claims (provider dependent):
- name
- given_name
- family_name
- email
- preferred_username / subject (sub)
- picture
- issuer (iss)
- groups / affiliations (if released)

## Purpose for the processing of personal data
Personal data and log files are collected and used for:
- User authentication and authorization at this service or trusted linked services
- Issuance, verification, and management of user attributes and invitations
- Automated sending of email messages necessary for service use (e.g. invitations, notifications)
- Service reliability, statistics, and development
- Security monitoring and incident response
- Integration and regression testing with test accounts

## Regular disclosure of personal data to third parties
Personal data is not regularly disclosed to third parties. Data may be shared with:
- Authorized KIT operational staff
- Linked services strictly for authorization decisions
- Incident response teams where required by policy or law

## Data retention
Personal identity claims from the IdP are cached only as needed for session and attribute issuance.
Attribute records and invitation metadata are stored while active and may be retained up to 24 months after last activity for audit/security unless earlier deletion is requested and permissible.
Access logs are deleted after 12 months.
X.509 (if a certificate issuance plugin is enabled) may require storing:
- A unique (pseudonymous) subject/issuer pair
- A copy or reference to the issued certificate on an external credential store (e.g. myproxy) for its validity period.

Users may request removal by contacting the service.

## Transfer of personal data outside the EU or EEA
Personal data is not intentionally transferred outside the EU/EEA. If a subprocessed service outside the EU is required, standard contractual safeguards will be applied.

## How to access, rectify and delete personal data
To rectify data released by your Home Organisation / IdP, contact its operators. For data stored by the Attribute Authority (attributes, invitations, logs), contact the service (see Contact Information) to request access, correction, or deletion (subject to legal/audit constraints).

## Data protection code of conduct
Personal data is protected according to the GÉANT Code of Conduct for Service Providers and applicable EU and German data protection law.

## Contact Information
Karlsruhe Institute of Technology (KIT) / SCC  
Herrmann-von-Helmholtz-Platz 1  
76344 Eggenstein-Leopoldshafen  
Tel: +49 721 6082 4659  
Service / operational contact: amin.mahnamfar@kit.edu  
Secondary contact: m-ops@lists.kit.edu  

KIT Helpdesk: http://www.scc.kit.edu/servicedesk/index.php