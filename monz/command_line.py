# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import click
import dateutil.parser
from babel.numbers import format_currency
from click_default_group import DefaultGroup
from pymonzo import MonzoAPI

from monz.utils import monzo_amount_to_dec


@click.group(cls=DefaultGroup, default='balance', default_if_no_args=True)
@click.option('--access-token', '-t', type=str, help="Monzo API access token.")
@click.pass_context
def cli(ctx, access_token):
    """
    Simple command line interface for quickly accessing your Monzo account info,
    current balance, latest transactions, etc.

    To use it you need to save your Monzo access token as 'MONZO_ACCESS_TOKEN'
    environment variable (export MOZNO_ACCESS_TOKEN='...') or pass it
    explicitly with each command.
    """
    try:
        ctx.obj['monzo_api'] = MonzoAPI(access_token=access_token)
    except ValueError as e:
        raise click.ClickException(e)


@cli.command()
@click.pass_context
def accounts(ctx):
    """Show connected Monzo accounts"""
    monzo_accounts = ctx.obj['monzo_api'].accounts()

    for n, account in enumerate(monzo_accounts, start=1):
        click.secho(
            "Account #{}, {}".format(n, account['description']),
            fg='green',
        )

        click.echo('{0:<12} {1}'.format('ID:', account['id']))
        click.echo('{0:<12} {1:%b %-d, %Y %-I:%M %p}'.format(
            'Created:', dateutil.parser.parse(account['created']))
        )

        if n != len(monzo_accounts):
            click.echo()  # Print a new line between accounts


@cli.command()
@click.option('--account-id', '-a', type=str, help="Monzo account ID.")
@click.pass_context
def balance(ctx, account_id):
    """Show Monzo account balance"""
    try:
        monzo_balance = ctx.obj['monzo_api'].balance(account_id=account_id)
    except ValueError as e:
        raise click.ClickException(e)

    amount = monzo_amount_to_dec(monzo_balance['balance'])
    local_amount = format_currency(amount, monzo_balance['currency'])

    local_spent_today = format_currency(
        monzo_balance['spend_today'], monzo_balance['currency']
    )

    click.secho(
        '{0:<12} {1}'.format('Balance:', local_amount),
        fg='green', bold=True,
    )
    click.echo('{0:<12} {1}'.format('Spent today:', local_spent_today))


@cli.command()
@click.option('--account-id', '-a', type=str, help="Monzo account ID.")
@click.option('--num', '-n', type=int, default=3,
              help="Number of transactions to show.")
@click.pass_context
def transactions(ctx, account_id, num):
    """Show Monzo account transactions"""
    try:
        monzo_transactions = ctx.obj['monzo_api'].transactions(
            account_id=account_id,
            reverse=True,
            limit=num,
        )
    except ValueError as e:
        raise click.ClickException(e)

    for n, transaction in enumerate(monzo_transactions, start=1):
        # We need a separate request for better merchant info
        trans = ctx.obj['monzo_api'].transaction(
            transaction_id=transaction['id'],
            expand_merchant=True,
        )
        merchant = trans['merchant']

        amount = monzo_amount_to_dec(trans['local_amount'])
        local_amount = format_currency(amount, trans['local_currency'])

        click.secho(
            '{0} at {1} ({2})'.format(
                local_amount,
                merchant['name'],
                merchant['address']['city'],
            ),
            fg='yellow', bold=True,
        )

        category = merchant['category'].replace('_', ' ').capitalize()
        click.echo('{0:<12} {1}'.format('Category:', category))

        if transaction['notes']:
            click.echo('{0:<12} {1}'.format('Notes:', transaction['notes']))

        click.echo('{0:<12} {1:%b %-d, %Y %-I:%M %p}'.format(
            'Date:', dateutil.parser.parse(transaction['created']))
        )

        if n != len(monzo_transactions):
            click.echo()  # Print a new line between transactions


if __name__ == '__main__':
    cli(obj={})
