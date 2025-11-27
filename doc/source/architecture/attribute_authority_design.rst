Attribute Authority Design Document
===================================

1. Overview
-----------

The Attribute Authority (AA) manages user attributes and entitlements used for authorization in OIDC/SAML-based federated infrastructures.

The AA:

- Stores attribute definitions (name, single-/multi-valued, value restrictions).
- Stores attribute values per user.
- Stores privilege rules describing who may perform which actions on which attributes/values of which targets.
- Exposes this information via APIs and issues entitlements following AARC guidelines.

A superadmin can assign privileges to other users. All authorization decisions are based on stored privilege tuples.

2. Core Data Model
------------------

2.1 Users
~~~~~~~~~

Represents principals that can hold attributes and perform actions.

**Table: ``users``**

- ``id`` (PK)
- ``subject_id`` (OIDC/SAML identifier)
- ``issuer``
- ``display_name``
- ``created_at``

2.2 Attribute Definitions
~~~~~~~~~~~~~~~~~~~~~~~~~

Represents schema-level information about attributes.

**Table: ``attributes``**

- ``id`` (PK)
- ``name`` (URN)
- ``cardinality`` (``single`` or ``multi``)
- ``value_restriction`` (JSON)
- ``description``
- ``enabled``

2.3 Attribute Values
~~~~~~~~~~~~~~~~~~~~

Represents stored attribute values for users.

**Table: ``user_attribute_values``**

- ``id`` (PK)
- ``user_id`` (FK → ``users``)
- ``attribute_id`` (FK → ``attributes``)
- ``value``
- ``created_at``
- ``updated_at``

Cardinality rules:

- ``single`` → max 1 row per (user, attribute)
- ``multi`` → many rows allowed

3. Privilege Model
------------------

3.1 Privilege Tuple
~~~~~~~~~~~~~~~~~~~

A privilege is defined as::

    (grantee_user_id, action, attribute_id?, value_restriction?, target_restriction?, passable)

**Table: ``privileges``**

- ``id`` (PK)
- ``grantee_user_id``
- ``action`` (enum)
- ``attribute_id`` (optional FK)
- ``value_restriction`` (JSON)
- ``target_restriction`` (JSON)
- ``passable`` (bool)
- ``created_at``

3.2 Actions
~~~~~~~~~~~

Attribute schema actions:

- ``create_attr``
- ``delete_attr``
- ``update_attr``
- ``read_attr``

Attribute value actions:

- ``set_value``
- ``add_value``
- ``remove_value``
- ``delete_value``
- ``read_value``

Privilege actions:

- ``assign_privilege``

3.3 Value Restrictions
~~~~~~~~~~~~~~~~~~~~~~

Constraints on which values are allowed.

Examples:

- regex: ``^urn:kit:group:iam:.*$``
- enum list
- prefix constraint

3.4 Target Restrictions
~~~~~~~~~~~~~~~~~~~~~~~

Constraints on which users can be modified by a privilege.

Example JSON rule::

    [
      { "eduPersonAffiliation": "^staff$", "orgUnit": "^Physics$" }
    ]

Semantics: privilege applies if at least one object in the list matches target user attributes.

3.5 Example Privileges
~~~~~~~~~~~~~~~~~~~~~~

Physics admin::

    grantee_user_id = 100
    action = ADD_VALUE
    attribute_id = entitlement
    value_restriction = "^urn:kit:group:physics:.*$"
    target_restriction = [
      { "eduPersonAffiliation": "^staff$", "orgUnit": "^Physics$" }
    ]
    passable = false

Superadmin::

    grantee_user_id = 1
    action = CREATE_ATTR
    attribute_id = NULL
    passable = true
