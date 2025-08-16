#!/usr/bin/env python3
"""
Quick script to fix Step Functions parameter mapping
"""
import json
import boto3

def fix_step_functions():
    # Load current definition
    with open('step_functions_def.json', 'r') as f:
        definition = json.load(f)
    
    # Fix the parameter mappings in the Gaussian training job
    env = definition['States']['GaussianTrainingJob']['Parameters']['Environment']
    
    # Update to use uppercase parameter names
    env['MAX_ITERATIONS.$'] = "States.Format('{}', $.MAX_ITERATIONS)"
    env['TARGET_PSNR.$'] = "States.Format('{}', $.TARGET_PSNR)"
    env['LOG_INTERVAL.$'] = "States.Format('{}', $.LOG_INTERVAL)"
    env['MODEL_VARIANT.$'] = "States.Format('{}', $.MODEL_VARIANT)"
    env['SH_DEGREE.$'] = "States.Format('{}', $.SH_DEGREE)"
    env['BILATERAL_PROCESSING.$'] = "States.Format('{}', $.BILATERAL_PROCESSING)"
    
    # Remove old lowercase references
    if 'max_iterations.$' in env:
        del env['max_iterations.$']
    if 'target_psnr.$' in env:
        del env['target_psnr.$']
    if 'log_interval.$' in env:
        del env['log_interval.$']
    if 'model_variant.$' in env:
        del env['model_variant.$']
    if 'sh_degree.$' in env:
        del env['sh_degree.$']
    if 'bilateral_processing.$' in env:
        del env['bilateral_processing.$']
    
    # Save fixed definition
    with open('step_functions_def_fixed.json', 'w') as f:
        json.dump(definition, f, indent=2)
    
    print("✅ Fixed Step Functions definition")
    
    # Update the state machine
    stepfunctions = boto3.client('stepfunctions', region_name='us-west-2')
    
    response = stepfunctions.update_state_machine(
        stateMachineArn='arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline',
        definition=json.dumps(definition)
    )
    
    print(f"✅ Updated state machine: {response['updateDate']}")

if __name__ == "__main__":
    fix_step_functions()
