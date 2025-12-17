# AutoMojo GitLab REST Client - Design Document

## Overview

The AutoMojo GitLab package provides a comprehensive, auto-generated REST client for interacting with the GitLab API. The design follows a modular, aspect-oriented architecture that prioritizes debuggability and readability over performance, in alignment with the repository's testing-focused mission.

## Architecture

### Core Components

#### 1. RestClientBase (`restclientbase.py`)
The foundation class that provides:
- **Authentication Management**: Handles Basic authentication with automatic retry on credential timeout
- **Session Management**: Manages HTTP sessions with configurable SSL verification
- **Aspect-Driven Execution**: Supports multiple execution patterns through the AspectsRest system
- **Error Handling**: Comprehensive HTTP error handling with detailed error messages

**Key Features:**
- Multiple action patterns (single call, retry until success, retry while success, etc.)
- Configurable timeouts and retry logic
- SSL certificate verification control for test environments
- Automatic re-authentication on credential failures

#### 2. AspectsRest (`aspectsrest.py`)
A configuration system that controls REST call behavior:
- **Action Patterns**: Defines how calls are executed (single, retry, polling)
- **Timeout Configuration**: Connection, completion, and inactivity timeouts
- **Logging Control**: Configurable logging patterns and intervals
- **Error Tolerance**: Allowed error codes and connection exceptions

**Supported Action Patterns:**
- `SINGLE_CALL`: Execute once, handle auth failures
- `SINGLE_CONNECTED_CALL`: Retry connection until timeout, execute once
- `DO_UNTIL_SUCCESS`: Retry until successful response
- `DO_WHILE_SUCCESS`: Continue while responses are successful
- `DO_UNTIL_CONNECTION_FAILURE`: Execute until connection fails

#### 3. GitLabRestClient (`clients/gitlabrestclient.py`)
The main client class that:
- Inherits from `RestClientBase`
- Provides organized access to API groups
- Auto-generated from OpenAPI specification
- Manages API group instances through properties

### Code Generation System

#### 4. RestClientGenerator (`generation/restclientgenerator.py`)
A sophisticated code generator that:
- **Parses OpenAPI Specifications**: Supports both JSON and YAML formats
- **Generates Type-Safe Code**: Creates strongly-typed parameter and response classes
- **Organizes by API Groups**: Groups related operations logically
- **Handles Complex Schemas**: Converts OpenAPI schemas to Python types
- **Creates Complete Modules**: Generates parameters, responses, and API group classes

**Generation Process:**
1. Parse OpenAPI specification
2. Extract operations and group by tags
3. Generate parameter classes with validation
4. Generate response wrapper classes
5. Generate API group classes with methods
6. Generate main client class with property access

#### 5. API Groups (`clients/groups/*.py`)
Auto-generated classes that:
- Inherit from `RestApiGroup`
- Provide method-based access to API endpoints
- Handle parameter validation and transformation
- Return strongly-typed response objects

#### 6. Parameter Classes (`clients/parameters/*.py`)
Auto-generated dataclasses that:
- Define required and optional parameters
- Provide type safety and validation
- Separate path, query, header, and body parameters
- Include default values from OpenAPI specification

#### 7. Response Classes (`clients/responses/*.py`)
Auto-generated wrapper classes that:
- Wrap raw HTTP responses
- Provide structured access to response data
- Handle JSON parsing with fallback to raw content
- Include status code and header access

### Supporting Components

#### 8. RestApiGroup (`restapigroup.py`)
Base class for API groups that:
- Maintains weak reference to parent client
- Provides access to client functionality
- Enables method chaining and composition

#### 9. ItemsResult (`itemsresult.py`)
Generic container for paginated results:
- **Paging Support**: Handles pagination metadata
- **Type Safety**: Generic type support for result items
- **Navigation**: Next/previous page functionality
- **Pre-canned Requests**: Stores callable requests for pagination

## Design Principles

### 1. Debuggability Over Performance
- Comprehensive error messages with context
- Detailed logging at multiple levels
- Clear separation of concerns
- Extensive parameter validation

### 2. Readability Over Conciseness
- Descriptive class and method names
- Comprehensive documentation strings
- Clear parameter separation (path, query, header, body)
- Explicit type annotations throughout

### 3. Aspect-Oriented Design
- Configurable execution behavior through aspects
- Separation of cross-cutting concerns (logging, retry, timeout)
- Consistent behavior across all API calls
- Easy customization for different environments

### 4. Code Generation Benefits
- **Consistency**: All API methods follow identical patterns
- **Maintainability**: Changes to patterns affect all generated code
- **Type Safety**: Strong typing throughout the API surface
- **Completeness**: Comprehensive coverage of GitLab API

## Key Features

### Authentication & Security
- Basic authentication with base64 encoding
- Automatic credential refresh on timeout
- Configurable SSL certificate verification
- Session reuse for performance

### Error Handling
- HTTP status code validation
- Detailed error messages with context
- Configurable allowed error codes
- Automatic retry on authentication failures

### Flexibility
- Multiple execution patterns via aspects
- Configurable timeouts and intervals
- Custom session support
- Environment-specific SSL handling

### Type Safety
- Generated parameter classes with validation
- Strongly-typed response objects
- Generic support for collections
- Optional parameter handling

## Usage Patterns

### Basic Usage
```python
from automojo.gitlab.rest.clients.gitlabrestclient import GitLabRestClient
from automojo.credentials.basiccredential import BasicCredential

credential = BasicCredential("username", "password")
client = GitLabRestClient("gitlab.example.com", credential)

# Access API groups through properties
admin_response = client.admin.some_operation(params)
```

### Advanced Usage with Aspects
```python
from automojo.gitlab.rest.aspectsrest import AspectsRest, ActionPattern

# Configure retry behavior
aspects = AspectsRest(
    action_pattern=ActionPattern.DO_UNTIL_SUCCESS,
    completion_timeout=300,
    retry_logging_interval=10
)

response = client.admin.some_operation(params, aspects=aspects)
```

### Pagination Support
```python
result = client.some_group.list_items(params)
while result.paging and result.paging.request_next:
    result = result.next_page_result()
    # Process result.items
```

## File Organization

```
source/packages/automojo/gitlab/rest/
├── aspectsrest.py              # Execution aspects configuration
├── restclientbase.py           # Base REST client functionality
├── restapigroup.py            # Base class for API groups
├── itemsresult.py             # Pagination support
├── restclientutils.py         # Utility functions (empty)
├── clients/
│   ├── gitlabrestclient.py    # Main client class (generated)
│   ├── groups/                # API group implementations (generated)
│   ├── parameters/            # Parameter classes (generated)
│   └── responses/             # Response classes (generated)
├── descriptions/
│   ├── gitlab-openapi-spec.yaml    # GitLab API specification
│   └── gitlab-openapi-hints.yaml  # Generation hints
└── generation/
    └── restclientgenerator.py # Code generation engine
```

## Testing Considerations

The design supports comprehensive testing through:
- **Configurable SSL verification** for test environments
- **Aspect-based behavior modification** for test scenarios
- **Detailed error reporting** for debugging test failures
- **Type-safe parameter construction** for test data creation
- **Response object inspection** for assertion writing

## Future Extensibility

The architecture supports future enhancements:
- **Additional Authentication Methods**: Easy to extend authentication in base class
- **Custom Response Processing**: Response classes can be extended
- **New Action Patterns**: Additional patterns can be added to aspects system
- **API Versioning**: Multiple client versions can coexist
- **Custom Serialization**: Parameter and response handling can be customized

This design provides a robust, maintainable, and extensible foundation for GitLab API integration while adhering to the repository's emphasis on debuggability and testing support.