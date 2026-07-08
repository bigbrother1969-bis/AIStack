# AI Runtime Architecture

## Purpose

This document describes how AI engines integrate with the AIStack Kernel architecture.

## Responsibility

The AI Runtime assists reasoning on governed knowledge.

It does not create authoritative knowledge.

## Operations

- reason
- explain
- summarize
- recommend
- validate_with_context
- generate_draft_artifact

## Ollama

Ollama is a possible local AI Engine implementation.

The Kernel shall not depend on Ollama.

## Principle

AI is a reasoning assistant, never a source of truth.
