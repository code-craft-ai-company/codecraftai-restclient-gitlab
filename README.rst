=======================
Code Craft AI GitLab
=======================

The ``codecraftai-gitlab`` package is the GitLab REST client for the ccai suite. It follows the same shape as ``codecraftai-restclient-github-public`` — building on ``codecraftai-restclient-base`` — but targets the GitLab REST API instead.

Highlights
==========

- ``GitLabRestClient`` as the top-level client, with ``RestApiGroup`` and ``RestClientBase`` supplying the base behaviours.
- Endpoint-group clients under ``rest/clients/`` split into parallel ``groups/``, ``parameters/``, and ``responses/`` modules.
- Coverage for standard GitLab resources: access requests, applications, branches, broadcast messages, clusters, jobs, pipelines, plan limits, and more.
- ``AspectsRest`` control of retry/timeout/action semantics.
- ``generation/restclientgenerator.py`` for regenerating the client from the GitLab OpenAPI spec.

Repository Structure
====================

- ``development/`` - Runtime environment scripts.
- ``repository-setup/`` - Repository homing and setup scripts.
- ``source/packages/`` - Package source code.
- ``source/testroots/testbase/`` - TestBase test roots.
- ``specs/`` - Requirements, design, and task documentation.
- ``userguide/`` - Standards, conventions, and documentation.

Environment Setup
=================

When working in a Codex container:

.. code-block:: bash

   ./development/setup-agent-container

For local development:

.. code-block:: bash

   ./repository-setup/rehome-repository
   ./development/setup-envrionment

Running Tests
=============

Activate the virtual environment:

.. code-block:: bash

   source .venv/bin/activate

Run TestBase tests (when test roots are populated):

.. code-block:: bash

   testbase testing run --root source/testroots/testbase --includes=ccai --output=./.output

Standards and Conventions
=========================

- Naming conventions: ``userguide/10-02-naming-conventions.rst``
- Code organization: ``userguide/10-01-code-organization.rst``
- Coding standards: ``userguide/10-00-coding-standards.rst``

Additional Resources
====================

- User guide entry point: ``userguide/userguide.rst``
- Design documentation: ``specs/design.md``
- Requirements: ``specs/requirements.md``
