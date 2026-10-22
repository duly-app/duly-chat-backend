# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/duly-app/duly-chat-backend/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                             |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/\_\_init\_\_.py                              |        0 |        0 |    100% |           |
| src/adapters/\_\_init\_\_.py                     |        0 |        0 |    100% |           |
| src/adapters/api/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| src/adapters/api/api\_adapter.py                 |       27 |        7 |     74% |26, 30, 39, 43, 47, 58, 62 |
| src/adapters/api/duly\_api.py                    |       62 |        6 |     90% |63, 66, 69, 107-112 |
| src/adapters/api/errors.py                       |        1 |        0 |    100% |           |
| src/adapters/security/\_\_init\_\_.py            |        3 |        0 |    100% |           |
| src/adapters/security/jwt\_codec.py              |       16 |        0 |    100% |           |
| src/adapters/security/service\_token\_service.py |       13 |        0 |    100% |           |
| src/adapters/security/token\_service.py          |       29 |        7 |     76% |34-40, 44, 50 |
| src/app.py                                       |       60 |       13 |     78% |68-110, 119 |
| src/bootstrap.py                                 |       40 |        0 |    100% |           |
| src/chatbot/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| src/chatbot/context/\_\_init\_\_.py              |        0 |        0 |    100% |           |
| src/chatbot/context/block\_type.py               |        5 |        0 |    100% |           |
| src/chatbot/context/context\_block.py            |       25 |        3 |     88% |21, 25, 39 |
| src/chatbot/context/context\_builder.py          |        6 |        0 |    100% |           |
| src/chatbot/errors.py                            |        2 |        0 |    100% |           |
| src/chatbot/loop.py                              |       39 |        1 |     97% |        80 |
| src/chatbot/loop\_result.py                      |       42 |        1 |     98% |        16 |
| src/chatbot/loop\_step.py                        |       48 |        1 |     98% |        45 |
| src/chatbot/threads/\_\_init\_\_.py              |        0 |        0 |    100% |           |
| src/chatbot/threads/thread\_store.py             |       50 |        0 |    100% |           |
| src/chatbot/tools/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| src/chatbot/tools/create\_note.py                |       13 |        0 |    100% |           |
| src/chatbot/tools/current\_time.py               |       17 |        4 |     76% |29-31, 34-36 |
| src/chatbot/tools/delete\_note.py                |       17 |        1 |     94% |        34 |
| src/chatbot/tools/embedding\_qa\_search.py       |       19 |        0 |    100% |           |
| src/chatbot/tools/get\_note.py                   |       17 |        0 |    100% |           |
| src/chatbot/tools/list\_notes.py                 |       22 |        4 |     82% |     82-85 |
| src/chatbot/tools/notes\_tool.py                 |       14 |        0 |    100% |           |
| src/chatbot/tools/registry.py                    |       27 |        0 |    100% |           |
| src/chatbot/tools/rendering.py                   |       28 |        1 |     96% |        48 |
| src/chatbot/tools/search\_notes.py               |       14 |        0 |    100% |           |
| src/chatbot/tools/tool.py                        |       23 |        1 |     96% |        49 |
| src/chatbot/tools/update\_note.py                |       21 |        3 |     86% | 36, 53-54 |
| src/chatbot/trace.py                             |       46 |        9 |     80% |43, 67, 82-84, 127, 139, 143, 170-172 |
| src/domain/\_\_init\_\_.py                       |        3 |        0 |    100% |           |
| src/domain/notes.py                              |        7 |        0 |    100% |           |
| src/domain/user.py                               |        4 |        0 |    100% |           |
| src/env.py                                       |       36 |        4 |     89% |29, 47-48, 63 |
| src/logs.py                                      |       26 |        1 |     96% |        51 |
| src/main.py                                      |        4 |        4 |      0% |       1-6 |
| **TOTAL**                                        |  **826** |   **71** | **91%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/duly-app/duly-chat-backend/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/duly-app/duly-chat-backend/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/duly-app/duly-chat-backend/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/duly-app/duly-chat-backend/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fduly-app%2Fduly-chat-backend%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/duly-app/duly-chat-backend/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.