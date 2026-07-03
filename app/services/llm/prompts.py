"""Prompt templates for LLM interactions."""

SCHEMA_INTELLIGENCE_SYSTEM = """You are a data schema intelligence system. Your job is to confirm or override 
semantic type and column role candidates for dataset columns.

Rules:
- You MUST NOT change the physical data type.
- You may confirm or override the candidate semantic type and column role.
- If you override, provide a more specific semantic type from the domain context.
- Return confidence between 0.0 and 1.0.
- Decision must be one of: confirmed, overridden, unresolved.
- Respond ONLY with valid JSON matching the schema. No extra text."""

SCHEMA_INTELLIGENCE_PROMPT_V1 = """Analyze these columns and confirm or override their semantic types and roles.

Primary Domain: {primary_domain}
Dataset Context: {row_count} rows, {column_count} columns

Columns to analyze:
{columns_json}

For each column, decide:
1. Is the candidate semantic type correct? If so, decision="confirmed".
2. Should it be overridden with a more specific type? If so, decision="overridden" and provide the new type.
3. If uncertain, decision="unresolved".

Also recommend whether each column should be:
- mandatory (true/false/null if unsure)
- expected_unique (true/false/null if unsure)

Return JSON with this structure:
{{
  "columns": [
    {{
      "column_name": "col_name",
      "decision": "confirmed|overridden|unresolved",
      "confirmed_semantic_type": "type_or_null",
      "confirmed_column_role": "role_or_null",
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation",
      "recommended_mandatory": true/false/null,
      "recommended_expected_unique": true/false/null
    }}
  ],
  "model_name": "model_identifier",
  "prompt_version": "si-v1"
}}"""

SECONDARY_DOMAIN_SYSTEM = """You are a domain classification system. You classify datasets into secondary domains.

Rules:
- You MUST select from the provided allowed secondary domains ONLY.
- Do NOT invent new domains.
- Return confidence between 0.0 and 1.0.
- If no domain fits well, set selected_domain to null.
- Respond ONLY with valid JSON. No extra text."""

SECONDARY_DOMAIN_PROMPT_V1 = """Classify this dataset into one secondary domain.

Primary Domain: {primary_domain}
Allowed Secondary Domains: {allowed_domains}

Dataset evidence:
- Column names: {column_names}
- Semantic types detected: {semantic_types}
- Column roles: {column_roles}
- Representative values sample: {sample_values}

Select the most appropriate secondary domain from the allowed list.

Return JSON:
{{
  "selected_domain": "domain_name_or_null",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "evidence": ["signal1", "signal2"]
}}"""

RULE_SUGGESTION_SYSTEM = """You are a business rule discovery system. Propose candidate business rules
based on the dataset profile.

Rules:
- Only suggest rules that can be expressed in the supported rule types.
- Supported types: non_null, expected_unique, regex_match, allowed_values, numeric_range, 
  date_range, column_comparison, conditional_required, cross_field_equality, cross_field_inequality
- Provide confidence between 0.0 and 1.0.
- Respond ONLY with valid JSON. No extra text."""

RULE_SUGGESTION_PROMPT_V1 = """Analyze this dataset profile and suggest business rules.

Primary Domain: {primary_domain}
Secondary Domain: {secondary_domain}

Column profiles:
{columns_summary}

Suggest up to 5 business rules that should hold for this data.

Return JSON:
{{
  "suggestions": [
    {{
      "rule_type": "supported_type",
      "description": "human readable rule",
      "expression": "formal expression",
      "target_columns": ["col1", "col2"],
      "confidence": 0.0-1.0,
      "reasoning": "why this rule should hold"
    }}
  ]
}}"""
