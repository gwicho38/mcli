#!/usr/bin/env python3
"""
Generate additional test documents for semantic search testing
"""

import sys
from pathlib import Path
from test_integration import IntegrationTest

def generate_more_documents():
    """Generate additional documents to test semantic search"""
    test = IntegrationTest()
    
    # Additional documents with varied content
    additional_pdfs = [
        {
            "filename": "machine_learning_tutorial.pdf",
            "content": """
            Machine Learning Tutorial
            
            Introduction to Machine Learning
            Machine learning is a subset of artificial intelligence that enables
            computers to learn and make decisions without being explicitly programmed.
            
            Types of Machine Learning
            1. Supervised Learning: Learning from labeled data
            2. Unsupervised Learning: Finding patterns in unlabeled data
            3. Reinforcement Learning: Learning through trial and error
            
            Common Algorithms
            - Linear Regression
            - Decision Trees
            - Neural Networks
            - Support Vector Machines
            - Random Forests
            
            Applications
            Machine learning is used in various fields including:
            - Healthcare: Disease diagnosis and drug discovery
            - Finance: Fraud detection and risk assessment
            - Marketing: Customer segmentation and recommendation systems
            - Transportation: Autonomous vehicles and route optimization
            """
        },
        {
            "filename": "data_science_guide.pdf",
            "content": """
            Data Science Guide
            
            What is Data Science?
            Data science is an interdisciplinary field that uses scientific methods,
            processes, algorithms, and systems to extract knowledge and insights
            from structured and unstructured data.
            
            Data Science Process
            1. Data Collection: Gathering data from various sources
            2. Data Cleaning: Removing errors and inconsistencies
            3. Data Exploration: Understanding patterns and relationships
            4. Feature Engineering: Creating new features from existing data
            5. Model Building: Training machine learning models
            6. Model Evaluation: Assessing model performance
            7. Deployment: Putting models into production
            
            Tools and Technologies
            - Python: Primary programming language
            - R: Statistical computing and graphics
            - SQL: Database querying
            - Tableau: Data visualization
            - Apache Spark: Big data processing
            
            Skills Required
            - Programming: Python, R, SQL
            - Statistics: Probability, hypothesis testing
            - Machine Learning: Algorithms and model selection
            - Data Visualization: Creating meaningful charts
            - Domain Knowledge: Understanding the business context
            """
        },
        {
            "filename": "artificial_intelligence_overview.pdf",
            "content": """
            Artificial Intelligence Overview
            
            Definition of AI
            Artificial Intelligence (AI) refers to the simulation of human
            intelligence in machines that are programmed to think and learn
            like humans.
            
            Types of AI
            1. Narrow AI: Designed for specific tasks
            2. General AI: Possesses human-like intelligence
            3. Superintelligent AI: Surpasses human intelligence
            
            AI Technologies
            - Machine Learning: Learning from data
            - Deep Learning: Neural networks with multiple layers
            - Natural Language Processing: Understanding human language
            - Computer Vision: Interpreting visual information
            - Robotics: Physical AI systems
            
            Current Applications
            - Virtual Assistants: Siri, Alexa, Google Assistant
            - Recommendation Systems: Netflix, Amazon, Spotify
            - Autonomous Vehicles: Tesla, Waymo
            - Healthcare: Medical diagnosis and treatment planning
            - Finance: Algorithmic trading and risk management
            
            Future Implications
            AI has the potential to revolutionize industries and create
            new opportunities while also raising important ethical and
            societal questions about automation and job displacement.
            """
        },
        {
            "filename": "python_programming_basics.pdf",
            "content": """
            Python Programming Basics
            
            Introduction to Python
            Python is a high-level, interpreted programming language known
            for its simplicity and readability. It's widely used in data
            science, web development, and automation.
            
            Basic Syntax
            - Variables: Store data values
            - Data Types: Integers, floats, strings, lists, dictionaries
            - Control Structures: If statements, loops, functions
            - Object-Oriented Programming: Classes and objects
            
            Key Features
            - Easy to learn and use
            - Extensive standard library
            - Cross-platform compatibility
            - Large community and ecosystem
            - Excellent for prototyping
            
            Common Libraries
            - NumPy: Numerical computing
            - Pandas: Data manipulation and analysis
            - Matplotlib: Data visualization
            - Scikit-learn: Machine learning
            - Django/Flask: Web development
            
            Best Practices
            - Write readable code with clear variable names
            - Use comments to explain complex logic
            - Follow PEP 8 style guidelines
            - Write unit tests for your code
            - Use virtual environments for project isolation
            """
        },
        {
            "filename": "database_design_principles.pdf",
            "content": """
            Database Design Principles
            
            What is Database Design?
            Database design is the process of creating a detailed data model
            of a database. It involves defining the structure, relationships,
            and constraints of the data to be stored.
            
            Design Principles
            1. Normalization: Eliminating data redundancy
            2. Data Integrity: Ensuring accuracy and consistency
            3. Performance: Optimizing query execution
            4. Scalability: Supporting growth and expansion
            5. Security: Protecting sensitive information
            
            Database Types
            - Relational Databases: MySQL, PostgreSQL, Oracle
            - NoSQL Databases: MongoDB, Cassandra, Redis
            - NewSQL Databases: CockroachDB, TiDB
            - Graph Databases: Neo4j, ArangoDB
            
            Key Concepts
            - Tables and Relationships
            - Primary and Foreign Keys
            - Indexes for Performance
            - Transactions and ACID Properties
            - Backup and Recovery Strategies
            
            Design Process
            1. Requirements Analysis: Understanding user needs
            2. Conceptual Design: Creating entity-relationship diagrams
            3. Logical Design: Converting to relational model
            4. Physical Design: Optimizing for performance
            5. Implementation: Creating the actual database
            """
        }
    ]
    
    print("📄 Generating additional test documents...")
    
    for pdf_info in additional_pdfs:
        pdf_path = test._create_dummy_pdf(pdf_info["filename"], pdf_info["content"])
        print(f"✅ Generated {pdf_info['filename']} ({pdf_path.stat().st_size} bytes)")
    
    print(f"📁 Documents saved to: {test.pdf_dir}")
    return test.pdf_dir

if __name__ == "__main__":
    generate_more_documents() 