---
title: "ABT Question OCR and Dataset generation"
author: "Amlan Talukder"
date: "2024-11-12"
---

## Introduction

These questions are from American Board of Toxicology (ABT) exams. For a few exams (2005-2007), the answers were provided in tabulated format within a non-pdf file (e.g. MS Excel and MS Word). For the rest, both the questions and answers were provided as scanned pdf format. These pdf files were processed using [Amazon Textract](https://aws.amazon.com/textract/) which has OCR capability and "Azure GPT-4o" model.

## Processing steps of the pdf files

The questions and the answers were processed using the following steps:

### Step 1:

- The pdf files were uploaded to Amazon S3, as Amazon Textract does not allow "multipage" processing for on-premise files
- The relevant pages with questions and answers were filtered and preprocessed using regular expressions
- GPT-4o were used to list the questions and answers (both in string and tabular format) using separate prompts
- Each pdf file was processed separately

  **Command**

  ```python
  python codes/extraction_questions.py
  ```

### Step 2:

- The pdf outputs were combined with the non-pdf data

  **Notebook**

  ```
  codes/combine_pdfs.ipynb
  ```

# Output format

The output file contains the following columns:

- _Question Index_: Consists of exam year, exam section (or part) and question number. For example, "2000A Q1" denotes the question 1 of the part A of the examination year 2000.
- _Question_: The question extracted as it was in the pdf
- _Options_: The options extracted as they were in the pdf
- _Question Source_: The source pdf file name that contains the question
- _Answers_: The answer choice(s) for the question
- _Answer Source_: The source pdf file name that contains the answer
